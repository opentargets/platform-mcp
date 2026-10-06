This server gives read-only access to the Open Targets Platform, a public resource integrating evidence on target-disease associations, drugs, variants, GWAS studies and credible sets. All data is retrieved through the Platform GraphQL API.

Recommended workflow:

1. Resolve identifiers. The API only accepts standardised IDs, so convert names (gene symbols, disease names, drug names, rsIDs) with `search_entities`, e.g. `search_entities(query_strings=["BRCA2", "breast cancer", "aspirin"])`. It returns up to 3 hits per query; pick the hit whose type matches the user's intent.
2. Learn the query structure. Call `get_open_targets_graphql_schema` with every category relevant to the question (be inclusive) and read its "COMMON MISTAKES TO AVOID" guidance. Use `get_type_dependencies` only as a fallback for a specific type, since its output can be large.
3. Query. Use `query_open_targets_graphql` for a single query and `batch_query_open_targets_graphql` to run the same query over many IDs instead of calling the single-query tool repeatedly.

Query tips:

- Request only the fields needed to answer the question; responses can be large.
- Paginated fields take `page: {index: 0, size: N}` and return a total `count` alongside `rows`.
- Query results report `status` ("success", "warning" or "error") with a `message`; on error, fix the query using the message and the schema rather than guessing field names.
- To report which data release answers are based on, query `meta { dataVersion { year month } }`.

Identifier formats:

- Targets: Ensembl gene IDs (e.g. "ENSG00000139618")
- Diseases/phenotypes: EFO, MONDO, HP or other ontology IDs (e.g. "MONDO_0007254", "EFO_0000305")
- Drugs: ChEMBL IDs (e.g. "CHEMBL25")
- Variants: "chr_pos_ref_alt" on GRCh38 (e.g. "19_44908822_C_T")
- Studies: study IDs (e.g. "GCST90002357")
- Credible sets: study locus IDs (e.g. "7d68cc9c70351c9dbd2a2c0c145e555d")
