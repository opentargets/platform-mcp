"""Tool for providing example GraphQL queries for the OpenTargets API."""

from pathlib import Path

from otar_mcp.mcp_instance import mcp


def _get_extracted_queries_path() -> Path:
    """Get the absolute path to the extracted_queries directory."""
    # The tool is in src/otar_mcp/tools/examples.py
    # extracted_queries is at the project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    return project_root / "extracted_queries"


def _clean_comment_line(line: str) -> str:
    """Remove comment marker from line."""
    return line[2:] if len(line) > 1 and line[1] == " " else line[1:]


def _parse_metadata_header(clean_line: str, metadata: dict) -> str | None:
    """Parse metadata header line and return current field or None.

    Args:
        clean_line: Cleaned comment line
        metadata: Metadata dictionary to update

    Returns:
        Current field name if multi-line, None otherwise
    """
    field_mappings = {
        "Query Name:": ("query_name", None),
        "Entity Type:": ("entity_type", None),
        "Description:": ("description", "description"),
        "Variables:": ("variables", "variables"),
        "Pagination Behavior:": ("pagination", None),
    }

    for prefix, (key, field) in field_mappings.items():
        if clean_line.startswith(prefix):
            value = clean_line.replace(prefix, "").strip()
            if value:
                metadata[key] = value
            return field

    return None


def _append_to_field(metadata: dict, field: str, text: str) -> None:
    """Append text to a metadata field."""
    if metadata[field]:
        metadata[field] += " " + text
    else:
        metadata[field] = text


def _parse_query_file(file_path: Path) -> dict:
    """Parse a .gql file and extract metadata and query content.

    Args:
        file_path: Path to the .gql file

    Returns:
        Dictionary with metadata fields and query string
    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    metadata = {
        "query_name": "",
        "entity_type": "",
        "description": "",
        "variables": "",
        "pagination": "",
        "query": "",
    }

    lines = content.split("\n")
    query_lines = []
    in_query = False
    current_field = None

    for line in lines:
        if line.startswith("#"):
            clean_line = _clean_comment_line(line)

            if clean_line.strip() == "":
                current_field = None
            else:
                new_field = _parse_metadata_header(clean_line, metadata)
                if new_field is not None:
                    current_field = new_field
                elif current_field in ("description", "variables"):
                    _append_to_field(metadata, current_field, clean_line.strip())
        elif line.strip().startswith("query ") or in_query:
            in_query = True
            query_lines.append(line)

    metadata["query"] = "\n".join(query_lines).strip()
    return metadata


def _format_queries_as_markdown(queries_by_category: dict) -> str:
    """Format queries as markdown documentation.

    Args:
        queries_by_category: Dictionary mapping category names to lists of query metadata

    Returns:
        Markdown-formatted string
    """
    markdown_parts = []

    markdown_parts.append("# Open Targets GraphQL Query Examples\n")
    markdown_parts.append("This document contains example GraphQL queries organized by category.\n")

    for category, queries in queries_by_category.items():
        # Add category header
        markdown_parts.append(f"\n## {category.capitalize()} Queries\n")
        markdown_parts.append(f"\n**Total queries in this category:** {len(queries)}\n")

        # Add each query
        for query_data in queries:
            query_name = query_data.get("query_name", "Unknown")
            description = query_data.get("description", "")
            variables = query_data.get("variables", "")
            pagination = query_data.get("pagination", "")
            query_string = query_data.get("query", "")

            markdown_parts.append(f"\n### {query_name}\n")

            if description:
                markdown_parts.append(f"\n**Description:** {description}\n")

            if variables:
                markdown_parts.append(f"\n**Variables:** {variables}\n")

            if pagination:
                markdown_parts.append(f"\n**Pagination:** {pagination}\n")

            markdown_parts.append("\n**Query:**\n")
            markdown_parts.append(f"```graphql\n{query_string}\n```\n")

    return "\n".join(markdown_parts)


@mcp.tool(name="get_open_targets_query_examples")
def get_open_targets_query_examples(categories: list[str]) -> str:
    """Retrieve example GraphQL queries for the Open Targets API organized by category.

    This tool loads query examples from the extracted_queries directory and formats them
    as comprehensive markdown documentation. The examples demonstrate common use cases
    and can be used as templates for writing custom queries.

    Available categories and their contents:

    - **target**: A therapeutic drug target representing a gene or protein. Queries return
      information about tractability, safety, baseline expression, molecular interactions,
      chemical probes, and gene essentiality data for specific targets.

    - **disease**: A medical condition or phenotypic trait associated with potential
      therapeutic interventions. Queries retrieve clinical signs and symptoms, disease
      classifications, and connections to relevant targets and drugs.

    - **drug**: A therapeutic compound or medication. Queries provide clinical precedence
      information, pharmacovigilance data, pharmacogenetics profiles, and associations
      with disease targets and clinical outcomes.

    - **evidence**: Target-disease associations supported by experimental or clinical data.
      The platform integrates publicly available datasets to score these relationships
      and assist in drug target prioritization.

    - **study**: A research investigation (GWAS, QTL studies) contributing data to the
      platform. Queries return study metadata, associated variants, and findings relevant
      to target-disease associations.

    - **variant**: A genetic sequence variation (SNPs, mutations). Queries retrieve genomic
      coordinates, disease associations, functional annotations, and connections to GWAS
      data and fine-mapping results.

    - **credibleset**: A collection of potentially causal genetic variants identified through
      fine-mapping analysis. Queries return variant groupings, posterior probabilities,
      and locus-specific information.

    - **search**: A query interface across all platform entities, enabling users to discover
      targets, diseases, drugs, evidence, studies, variants, and credible sets through
      keyword or structured searches.

    Args:
        categories: List of category names to include (e.g., ["target", "disease", "drug"]).
                   Must be one or more of the available categories listed above.

    Returns:
        str: Markdown-formatted documentation containing all queries from the requested
             categories, with descriptions, variables, pagination info, and GraphQL code.

    Raises:
        ValueError: If an invalid category is provided or if no categories are specified
        FileNotFoundError: If the extracted_queries directory does not exist

    Example:
        >>> examples = get_open_targets_query_examples(["target", "disease"])
        >>> # Returns markdown with all target and disease query examples
    """
    # Get path to extracted_queries directory
    queries_dir = _get_extracted_queries_path()

    if not queries_dir.exists():
        msg = (
            f"Extracted queries directory not found at {queries_dir}. "
            "Please ensure the extracted_queries folder exists in the project root."
        )
        raise FileNotFoundError(msg)

    # Get valid categories from directory structure
    valid_categories = {
        d.name
        for d in queries_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("__")
    }

    # Validate categories
    requested_categories = set(categories)
    invalid = requested_categories - valid_categories
    if invalid:
        valid_list = ", ".join(sorted(valid_categories))
        msg = f"Invalid categories: {invalid}. Valid categories are: {valid_list}"
        raise ValueError(msg)

    # Load queries for each requested category
    queries_by_category = {}

    for category in categories:
        category_path = queries_dir / category

        # Find all .gql files in this category
        gql_files = sorted(category_path.glob("*.gql"))

        queries = []
        for gql_file in gql_files:
            try:
                query_data = _parse_query_file(gql_file)
                queries.append(query_data)
            except Exception as e:
                # If parsing fails, skip this file but continue
                print(f"Warning: Failed to parse {gql_file}: {e}")
                continue

        if queries:
            queries_by_category[category] = queries

    # Format as markdown
    markdown_output = _format_queries_as_markdown(queries_by_category)

    return markdown_output
