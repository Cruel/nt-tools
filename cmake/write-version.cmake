include("${CMAKE_CURRENT_LIST_DIR}/noveltea_bgfx_version.cmake")

if(NOT OUTPUT OR NOT PACKAGE_NAME OR NOT TAG)
    message(FATAL_ERROR "OUTPUT, PACKAGE_NAME, and TAG are required")
endif()
string(TIMESTAMP BUILT_AT_UTC "%Y-%m-%dT%H:%M:%SZ" UTC)
file(WRITE "${OUTPUT}" "package: ${PACKAGE_NAME}\n"
    "tag: ${TAG}\n"
    "target: linux-x64\n"
    "bgfx_cmake_release: v${NOVELTEA_SHADERC_BGFX_RELEASE}\n"
    "bgfx_cmake_sha256: ${NOVELTEA_SHADERC_BGFX_ARCHIVE_SHA256}\n"
    "built_at_utc: ${BUILT_AT_UTC}\n")
