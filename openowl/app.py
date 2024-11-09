import streamlit as st

from openowl.clients import OpenOwlClient
from openowl.depsdev_utils import extract_package_url, get_deps_table
from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


def main():
    oowl_client = OpenOwlClient()

    st.set_page_config(
        page_title="OpenOwl",
        page_icon="🦉",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Dependency Scan")

    # Move configuration to sidebar
    with st.sidebar:
        package_manager = st.selectbox("Package Manager", ["pypi", "npm"])
        package_name = st.text_input("Package Name", "pandas")

        package_versions = oowl_client.get_package_versions(
            package_manager, package_name
        )
        package_versions.sort(reverse=True)
        package_version = st.selectbox("Package Version", package_versions)

    # Main content area
    st.markdown(
        f"""
        Package name: `{package_name}`, package manager: `{package_manager}`, package version: `{package_version}`
        """
    )

    # Scan package with deps.dev api
    res = oowl_client.scan_from_package_name(
        package_manager, package_name, package_version
    )

    package_url = extract_package_url(res)
    if package_url is None:
        with st.sidebar:
            st.markdown("---")  # Visual separator
            st.markdown(
                "No repository URL found automatically. Please provide it manually:"
            )
            package_url = st.text_input(
                "GitHub Repository URL", placeholder="https://github.com/owner/repo"
            )
    else:
        st.markdown(f"Package URL: {package_url}")

    df_deps = get_deps_table(res["package_dependencies"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("total number of dependencies", res["num_deps_total"])
    with col2:
        st.metric("direct dependencies", res["num_deps_direct"])
    with col3:
        st.metric("indirect dependencies", res["num_deps_indirect"])

    st.dataframe(
        df_deps.loc[df_deps["relation"].isin(["DIRECT", "INDIRECT"])],
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
