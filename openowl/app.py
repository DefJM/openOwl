import os
from pathlib import Path

import streamlit as st
from tinydb import TinyDB

from openowl.clients import DepsDevClient, OpenOwlClient
from openowl.depsdev_utils import get_deps_table
from openowl.gh_sentiment_analysis import create_toxicity_dataframe
from openowl.graphs import create_score_scatter_plot
from openowl.logger_config import setup_logger
from openowl.utils import (extract_github_info, extract_package_info,
                           sort_version_list)

logger = setup_logger(__name__)


def render_sidebar(oowl_client):
    with st.sidebar:
        package_manager = st.selectbox("Package Manager", ["pypi", "npm"])
        package_github_url = st.text_input(
            "GitHub URL", "https://github.com/pandas-dev/pandas"
        )
        _, package_name = extract_github_info(package_github_url)

        package_versions = oowl_client.get_package_versions(
            package_manager, package_name
        )
        package_versions = sort_version_list(package_versions)
        package_version = st.selectbox("Package Version", package_versions)
        package_info = extract_package_info(
            package_manager, package_github_url, package_version
        )
        return package_info


def render_community_metrics(db, package_info):
    st.write(f"# {package_info['name']} {package_info['version']} - Community metrics")
    st.markdown(
        f"""
        Package manager: `{package_info['package_manager']}`, 
        GitHub URL: {package_info['github_url']}
        """
    )

    df = create_toxicity_dataframe(db, package_info)

    # Try to show the toxicity plot if data is available
    if "toxicity_llm_score" in df.columns:
        df_filtered = df[df["toxicity_llm_score"].notna()]
        st.plotly_chart(
            create_score_scatter_plot(
                df_filtered,
                comment_column="comment_details",
                group_column="issue_id",
                score_column="toxicity_llm_score",
            )
        )
    else:
        st.warning("LLM toxicity scores are not yet available for this package.")

    # Try to show negative reactions plot ("-1") if data is available
    if "reactions_minus1" in df.columns:
        df_filtered = df[df["reactions_minus1"].notna()]
        st.plotly_chart(
            create_score_scatter_plot(
                df_filtered,
                comment_column="comment_details",
                group_column="issue_id",
                score_column="reactions_minus1",
            )
        )
    else:
        st.warning("Negative reactions data is not yet available for this package.")

    # Show the dataframe in an expander below the plot
    with st.expander("View detailed data"):
        st.dataframe(df, use_container_width=True)


def render_dependencies(res):
    st.markdown("# Sub-dependencies")
    # render metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("total number of dependencies", res["num_deps_total"])
    with col2:
        st.metric("direct dependencies", res["num_deps_direct"])
    with col3:
        st.metric("indirect dependencies", res["num_deps_indirect"])

    # render dependency table
    df_deps = get_deps_table(res["package_dependencies"])
    df_deps = df_deps.sort_values(
        by="relation", key=lambda x: x.map({"SELF": 0, "DIRECT": 1, "INDIRECT": 2})
    )
    st.dataframe(df_deps, use_container_width=True)


def main():
    base_url = os.getenv("OPEN_OWL_CLIENT_BASE_URL", "http://127.0.0.1:8000")
    oowl_client = OpenOwlClient(base_url=base_url)
    db = TinyDB(Path(os.environ.get("PATH_DB")))

    st.set_page_config(
        page_title="OpenOwl",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Render sidebar and get inputs
    package_info = render_sidebar(oowl_client)

    # Render community metrics
    render_community_metrics(db, package_info)

    # Obtain and render subdependencies with deps.dev api
    res = oowl_client.scan_from_package_name(
        package_info["package_manager"], package_info["name"], package_info["version"]
    )
    render_dependencies(res)


if __name__ == "__main__":
    main()
