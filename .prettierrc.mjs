import baseConfig from "@prb/devkit/prettier";

const config = {
  ...baseConfig,
  printWidth: 100,
  overrides: [
    ...(baseConfig.overrides ?? []),
    {
      files: "*.md",
      options: {
        proseWrap: "preserve",
      },
    },
  ],
};

export default config;
