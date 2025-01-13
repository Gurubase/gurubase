import { fixupConfigRules, fixupPluginRules } from "@eslint/compat";
import _import from "eslint-plugin-import";
import react from "eslint-plugin-react";
import prettier from "eslint-plugin-prettier";
import simpleImportSort from "eslint-plugin-simple-import-sort";
import globals from "globals";
import path from "node:path";
import { fileURLToPath } from "node:url";
import js from "@eslint/js";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
    baseDirectory: __dirname,
    recommendedConfig: js.configs.recommended,
    allConfig: js.configs.all
});

export default [...fixupConfigRules(compat.extends(
    // "next/core-web-vitals",
    "eslint:recommended",
    "plugin:import/recommended",
    // "plugin:import/typescript",
    "plugin:react/recommended",
    "plugin:prettier/recommended",
    "eslint-config-prettier",
)), {
    plugins: {
        import: fixupPluginRules(_import),
        react: fixupPluginRules(react),
        prettier: fixupPluginRules(prettier),
        "simple-import-sort": simpleImportSort,
    },

    languageOptions: {
        globals: {
            ...globals.node,
            ...globals.browser,
        },
    },

    settings: {
        react: {
            version: "detect",
        },

        "import/resolver": {
            node: {
                extensions: [".js", ".jsx"],
                moduleDirectory: ["node_modules", "src/"],
                paths: ["src"],
            },

            alias: {
                map: [["@", "./src"]],
                extensions: [".js", ".jsx"],
            },
        },
    },

    rules: {
        "simple-import-sort/imports": "error",
        "simple-import-sort/exports": "error",
        "import/first": "error",
        "import/newline-after-import": "error",
        "import/no-duplicates": "error",
        "import/no-unresolved": "error",
        "import/no-unused-modules": "error",
        "react/prop-types": "off",
        "react/react-in-jsx-scope": "off",

        "react/jsx-sort-props": ["error", {
            callbacksLast: true,
            shorthandFirst: true,
            ignoreCase: true,
            reservedFirst: true,
        }],

        "no-unused-vars": "error",

        "no-console": ["warn", {
            allow: ["warn", "error"],
        }],

        "prettier/prettier": ["error", {
            arrowParens: "always",
            bracketSpacing: true,
            endOfLine: "lf",
            htmlWhitespaceSensitivity: "css",
            singleAttributePerLine: false,
            bracketSameLine: true,
            jsxSingleQuote: false,
            printWidth: 80,
            proseWrap: "preserve",
            quoteProps: "as-needed",
            semi: true,
            singleQuote: false,
            tabWidth: 2,
            trailingComma: "none",
            useTabs: false,
        }],

        "no-multiple-empty-lines": ["error", {
            max: 1,
            maxEOF: 0,
        }],

        "padding-line-between-statements": ["error", {
            blankLine: "always",
            prev: "*",
            next: "return",
        }, {
            blankLine: "always",
            prev: ["const", "let", "var"],
            next: "*",
        }, {
            blankLine: "any",
            prev: ["const", "let", "var"],
            next: ["const", "let", "var"],
        }],

        "import/extensions": ["error", "never", {
            js: "never",
            jsx: "never",
        }],
    },
}];