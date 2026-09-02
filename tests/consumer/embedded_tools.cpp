extern int noveltea_bgfx_shaderc_embedded_cli_main(int argc, const char* argv[]);
extern int noveltea_bimg_texturec_main(int argc, const char* argv[]);

extern "C" int noveltea_toolchain_smoke(int argc, const char* argv[])
{
    return noveltea_bgfx_shaderc_embedded_cli_main(argc, argv)
        + noveltea_bimg_texturec_main(argc, argv);
}
