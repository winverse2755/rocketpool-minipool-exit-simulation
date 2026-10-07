# Snapshot provenance

Inputs copied byte-for-byte from the audited Phases 1–3 pipeline in the user's dataScrapping workspace. No live data is mixed into this analysis.

- Execution block: 26,127,238, hash `0x1bf0be7e400778524a55c4d8bc4228e9c58f7455468ca11571532deb9056abd3`.
- UTC timestamp: 2026-10-05T16:03:35+00:00.
- Beacon slot: 15,366,016; state root: `0x547481680d4edb8150b8c1ad5b068350d8b5dc1f7845a0f15a29e7c703c9c5ab`.
- ETH/rETH rate, integer wei: `1173167372147210985`.
- Registry: 42,317 registered; 14,099 contract-staking/unfinalised, exactly matching protocol total and re-enumerated address set.
- Beacon join: 14,099 unique pubkeys and validator indices, from 71 saved validators POST batches at the state root, finalized and non-optimistic. Beacon execution payload hash matched the execution block.
- Eligible: 11,571 active_ongoing, far-future exit epoch, unslashed minipools on 1,323 node addresses. Excluded: 2,473 active_exiting, 39 withdrawal_done, 16 withdrawal_possible.
- All bonds: 8 or 16 ETH; observed user deposits match 32 minus bond.
- Node RPL: total staked = legacy + megapool, queried once per node at B; unstaking RPL excluded. Values repeat in minipool rows and must be deduplicated by node.
- Megapool active count is the contract bond-requirement count and can include queued/exiting validators; it is not proof of beacon active_ongoing status.
- Near-snapshot RocketDash cross-check: API block 26,127,268 (30 later); exact staking minipool count and exact protocol total/legacy/megapool staked RPL agreement.

RocketStorage was checked against [official documentation](https://docs.rocketpool.net/en/protocol/contracts-integrations): `0x1d8f8f00cfa6758d7bE78336684788Fb0ee0Fa46`. All other Rocket Pool addresses/ABIs were resolved through RocketStorage at B. Public execution RPC: https://rpc.mevblocker.io; beacon API: https://ethereum-beacon-api.publicnode.com.

The collector used Multicall3 to batch minipool status, finalisation, node, commission, bond, user deposit and pubkey reads. Node RPL used Saturn's getNodeStakedRPL/getNodeLegacyStakedRPL/getNodeMegapoolStakedRPL. Registry and on-chain/beacon reconciliation happened upstream; the published simulation validates input consistency offline but does not repeat the chain collection.

Specification Markdown in [sources](sources) was saved during Phase 0 collection (5 October 2026). RPIP-71 and RPIP-80 live pages were checked again on 7 October 2026.

Input SHA-256:

- [minipools.csv](minipools.csv): `302be2bbd6f04354b96bde86120c16a3269d92406def8e4f5f15a7e1463b6985`
- [nodes.csv](nodes.csv): `6ea7ff60d92fe469f37a3cf24b2fe410ecbce6c40ece5cddc64384cdac9c1473`
- [snapshot.json](snapshot.json): `e3b04c5dc993e70778a9cedb91acedf0f0f0cbdaa73b46dc70014e4e37ac8752`
