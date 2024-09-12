from pprint import pprint

import streamlit as st

from openowl.clients import OpenOwlClient
from openowl.depsdev_utils import get_deps_table
from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


def main():
    oowl_client = OpenOwlClient()

    st.title("Dependency Scan")
    package_url = st.text_input("Package URL", "https://github.com/pandas-dev/pandas")

    # Scan with package version
    res = oowl_client.scan_from_url(package_url)
    df_deps = get_deps_table(res["package_dependencies"])

    st.markdown(
        f"""
                Current default version of :green-background[{res["package_name"]}] is: :green-background[{res["package_version"]}].
                """
    )

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
