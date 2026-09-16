extern int noveltea_bimg_texturec_main(int argc, const char* argv[]);

// Referencing standalone miniz as well as texturec forces the linker to extract
// both miniz and bimg's image decoder from the packaged static closure.
extern "C" const char* mz_version();

int main(int argc, const char* argv[])
{
    if (mz_version() == nullptr)
    {
        return 1;
    }

    return noveltea_bimg_texturec_main(argc, argv);
}
