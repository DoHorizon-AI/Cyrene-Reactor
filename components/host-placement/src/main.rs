//! ┌─────────────────────────────────────────────────────────────────────┐
//! │  📄 main.rs                                                       │
//! │  Module: reactor_host_placement                                  │
//! │  Role: Adapt confirmed host facts to canonical Platform placement.│
//! │  模块职责：复用平台放置算法，保持 Lease 为唯一分配权威。                 │
//! └─────────────────────────────────────────────────────────────────────┘

use std::collections::{BTreeMap, BTreeSet};
use std::io::{self, Read};
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::{bail, Context, Result};
use cy_execution_fabric::{
    execution_capability, plan_execution_placement, ArtifactAvailability, ArtifactPlacementQuote,
    ExecutionPlacementRequest, ExecutionTargetCandidate, NetworkRequirements, PlacementPolicy,
};
use cy_kernel_contract::{
    Capability, CapabilityRequirement, Identity, Provider, ProviderSnapshot, ProviderState,
    Quantity, Resource, ResourceQuery, ResourceState, TopologyLink,
};
use cy_manifest::ArtifactRef;
use cy_proto::{
    core_v1::{ExecutionAttachmentType, KernelCapabilities, NodeLifecycleState, RestartCapability},
    semantic_v1,
};
use prost::Message;
use serde::Deserialize;
use serde_json::json;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    capabilities: Vec<u8>,
    node_id: String,
    node_epoch: u64,
    minimum_memory_bytes: u64,
    artifact: ArtifactRef,
    scope: String,
}

fn resource_from_proto(resource: semantic_v1::Resource) -> Result<Resource> {
    let identity = resource.identity.context("RESOURCE_IDENTITY_MISSING")?;
    let provider = resource.provider.context("RESOURCE_PROVIDER_MISSING")?;
    let state = match semantic_v1::ResourceState::try_from(resource.state) {
        Ok(semantic_v1::ResourceState::Ready) => ResourceState::Ready,
        Ok(semantic_v1::ResourceState::Degraded) => ResourceState::Degraded,
        Ok(semantic_v1::ResourceState::Unavailable) => ResourceState::Unavailable,
        Ok(semantic_v1::ResourceState::Unspecified) | Err(_) => {
            bail!("RESOURCE_STATE_INVALID: state must be known and specified")
        }
    };
    let links = resource
        .links
        .into_iter()
        .map(|link| {
            let peer = link.peer.context("TOPOLOGY_PEER_MISSING")?;
            Ok(TopologyLink {
                peer: identity_from_proto(peer),
                kind: link.kind,
                properties: link.properties.into_iter().collect(),
            })
        })
        .collect::<Result<Vec<_>>>()?;
    let mapped = Resource {
        identity: identity_from_proto(identity),
        provider: identity_from_proto(provider),
        resource_class: resource.resource_class,
        capabilities: resource
            .capabilities
            .into_iter()
            .map(|capability| Capability {
                id: capability.id,
                revision: capability.revision,
                properties: capability.properties.into_iter().collect(),
            })
            .collect(),
        capacity: resource
            .capacity
            .into_iter()
            .map(|(key, quantity)| {
                (
                    key,
                    Quantity {
                        value: quantity.value,
                        unit: quantity.unit,
                    },
                )
            })
            .collect(),
        attributes: resource.attributes.into_iter().collect(),
        state,
        reason_code: resource.reason_code,
        summary: resource.summary,
        links,
    };
    mapped
        .validate()
        .map_err(|error| anyhow::anyhow!("{}: {}", error.reason_code, error.message))?;
    Ok(mapped)
}

fn identity_from_proto(identity: semantic_v1::Identity) -> Identity {
    Identity {
        id: identity.id,
        generation: identity.generation,
    }
}

fn main() -> Result<()> {
    let mut input = String::new();
    io::stdin()
        .take(4 * 1024 * 1024)
        .read_to_string(&mut input)?;
    let input: Input = serde_json::from_str(&input)?;
    let facts = KernelCapabilities::decode(input.capabilities.as_slice())?;
    let node = facts.node.context("NODE_IDENTITY_MISSING")?;
    if node.node_id != input.node_id || node.node_epoch != input.node_epoch {
        bail!("NODE_VERSION_CHANGED: refresh and confirm the execution node");
    }
    let now = u64::try_from(SystemTime::now().duration_since(UNIX_EPOCH)?.as_millis())?;
    let sampled = facts.observed_at.context("NODE_OBSERVATION_MISSING")?;
    let sampled =
        u64::try_from(sampled.seconds)? * 1_000 + u64::try_from(sampled.nanos)? / 1_000_000;
    let resources = facts
        .resources
        .into_iter()
        .map(resource_from_proto)
        .collect::<std::result::Result<Vec<_>, _>>()
        .map_err(|error| anyhow::anyhow!("{}", error))?;
    let provider = resources
        .iter()
        .find(|resource| {
            resource
                .capabilities
                .iter()
                .any(|cap| cap.id == "vendor.nvidia.cuda")
        })
        .context("CUDA_RESOURCE_UNAVAILABLE")?
        .provider
        .clone();
    let resources = resources
        .into_iter()
        .filter(|r| r.provider == provider)
        .collect();
    let peer = format!("artifact-peer:{}", node.node_id);
    let query = ResourceQuery {
        resource_class: "accelerator".to_string(),
        count: 1,
        required_capabilities: vec![CapabilityRequirement {
            id: "vendor.nvidia.cuda".to_string(),
            minimum_revision: 1,
            required_properties: BTreeMap::new(),
        }],
        minimum_capacity: BTreeMap::from([(
            "memory.allocatable".to_string(),
            Quantity {
                value: input.minimum_memory_bytes,
                unit: "byte".to_string(),
            },
        )]),
    };
    let request = ExecutionPlacementRequest {
        capability_requirements: Vec::new(),
        resource_query: query,
        allowed_attachments: BTreeSet::from([ExecutionAttachmentType::HostAgent]),
        persistent: Some(true),
        restart_capability: Some(RestartCapability::None),
        checkpoint_resume: false,
        network: NetworkRequirements::default(),
        artifacts: vec![input.artifact.clone()],
        artifact_policy_scope: input.scope.clone(),
        policy: PlacementPolicy {
            required_trust_domain: Some(input.scope.clone()),
            ..Default::default()
        },
        latest_start_unix_ms: None,
        now_unix_ms: now,
    };
    let candidate = ExecutionTargetCandidate {
        node: node.clone(),
        lifecycle_state: NodeLifecycleState::Online,
        attachment: ExecutionAttachmentType::HostAgent,
        persistent: true,
        restart_capability: RestartCapability::None,
        capabilities: vec![execution_capability(
            ExecutionAttachmentType::HostAgent,
            true,
            RestartCapability::None,
        )],
        provider: Provider {
            identity: provider.clone(),
            state: ProviderState::Ready,
            capabilities: Vec::new(),
        },
        provider_snapshot: ProviderSnapshot {
            provider,
            snapshot_generation: facts.inventory_generation,
            resources,
            workers: Vec::new(),
            endpoints: Vec::new(),
            sampled_at_unix_ms: sampled,
            expires_at_unix_ms: sampled + 10_000,
        },
        residency: "configured-host".to_string(),
        trust_domain: input.scope.clone(),
        classifications: BTreeSet::new(),
        policy_tags: BTreeSet::new(),
        artifact_destination_peer_id: peer.clone(),
        artifact_quotes: vec![ArtifactPlacementQuote {
            quote_id: format!("verified:{}", input.artifact.digest),
            artifact: input.artifact,
            destination_peer_id: peer,
            policy_scope: input.scope,
            observed_at_unix_ms: sampled,
            valid_until_unix_ms: sampled + 10_000,
            availability: ArtifactAvailability::VerifiedLocal {
                inventory_generation: facts.inventory_generation,
            },
        }],
        execution_cost_microunits: 0,
        available_at_unix_ms: now,
        reliability_score: 0,
    };
    let decision = plan_execution_placement(&request, &[candidate])?;
    let evaluation = &decision.evaluations[0];
    let reasons = evaluation
        .reasons
        .iter()
        .map(|r| json!({"code": r.reason_code, "message": r.message}))
        .collect::<Vec<_>>();
    println!(
        "{}",
        json!({"eligible": evaluation.eligible, "nodeRef": {"nodeId": node.node_id, "nodeEpoch": node.node_epoch}, "reasons": reasons})
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    fn valid_resource() -> semantic_v1::Resource {
        semantic_v1::Resource {
            identity: Some(semantic_v1::Identity {
                id: "gpu-0".to_string(),
                generation: 1,
            }),
            provider: Some(semantic_v1::Identity {
                id: "nvidia-0".to_string(),
                generation: 2,
            }),
            resource_class: "accelerator".to_string(),
            capabilities: vec![semantic_v1::Capability {
                id: "vendor.nvidia.cuda".to_string(),
                revision: 1,
                properties: HashMap::new(),
            }],
            capacity: HashMap::from([(
                "memory.allocatable".to_string(),
                semantic_v1::Quantity {
                    value: 24 * 1024 * 1024 * 1024,
                    unit: "byte".to_string(),
                },
            )]),
            attributes: HashMap::new(),
            state: semantic_v1::ResourceState::Ready as i32,
            reason_code: "resource.ready".to_string(),
            summary: "available".to_string(),
            links: Vec::new(),
        }
    }

    #[test]
    fn converts_public_resource_contract_without_adapter_client() {
        let resource = resource_from_proto(valid_resource()).expect("valid resource");
        assert_eq!(resource.identity.id, "gpu-0");
        assert_eq!(resource.provider.id, "nvidia-0");
        assert_eq!(resource.state, ResourceState::Ready);
        assert_eq!(resource.capabilities[0].id, "vendor.nvidia.cuda");
    }

    #[test]
    fn rejects_unspecified_resource_state() {
        let mut input = valid_resource();
        input.state = semantic_v1::ResourceState::Unspecified as i32;
        let error = resource_from_proto(input).expect_err("unspecified state must fail closed");
        assert!(error.to_string().contains("RESOURCE_STATE_INVALID"));
    }

    #[test]
    fn rejects_missing_topology_peer() {
        let mut input = valid_resource();
        input.links.push(semantic_v1::TopologyLink {
            peer: None,
            kind: "pcie".to_string(),
            properties: HashMap::new(),
        });
        let error = resource_from_proto(input).expect_err("missing peer must fail closed");
        assert!(error.to_string().contains("TOPOLOGY_PEER_MISSING"));
    }
}
