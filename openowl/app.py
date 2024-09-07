from pprint import pprint

import streamlit as st

from openowl.clients import OpenOwlClient
from openowl.depsdev_utils import get_deps_table
from openowl.logger_config import setup_logger
from openowl.utils import extract_github_library_name, is_github_repo

logger = setup_logger(__name__)

oowl_client = OpenOwlClient()

st.title("Dependency Scan")
package_url = st.text_input("Package URL", "https://github.com/pandas-dev/pandas")

# Scan with package version
res = oowl_client.scan_from_url(package_url)

st.markdown(f"""
            Current default version of :green-background[{res["package_name"]}] is: :green-background[{res["package_version"]}].
            """)
df_deps = get_deps_table(res["package_dependencies"])
df_deps = df_deps[1:].sort_values("relation")

num_deps_total = len(df_deps)
num_deps_direct = len(df_deps.loc[df_deps["relation"]=="DIRECT"])
num_deps_indirect = len(df_deps.loc[df_deps["relation"]=="INDIRECT"])

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("total number of dependencies", num_deps_total)    
with col2:
    st.metric("direct dependencies", num_deps_direct)
with col3:
    st.metric("indirect dependencies", num_deps_indirect)
st.dataframe(df_deps[1:], use_container_width=True)