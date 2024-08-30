import requests
import streamlit as st
from pprint import pprint

from openowl.clients import OpenOwlClient
from openowl.logger_config import setup_logger
from openowl.depsdev_utils import get_deps_table

oowl_client = OpenOwlClient()

st.title("Dependency Scan")
package_name = st.text_input("Package URL", "https://github.com/pandas-dev/pandas")


# Scan with package version
res = oowl_client.scan_from_url(
    "https://github.com/pandas-dev/pandas",
    package_version="2.2.2"
)
df_deps = get_deps_table(res["package_dependencies"])
st.dataframe(df_deps, use_container_width=True)


