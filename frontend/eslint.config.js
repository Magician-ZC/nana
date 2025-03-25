import globals from 'globals'
import js from '@eslint/js'
import eslintPluginVue from 'eslint-plugin-vue'

export default [
  js.configs.recommended,
  {
    files: ['**/*.js', '**/*.vue'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node
      },
      sourceType: 'module',
      ecmaVersion: 'latest',
    },
    plugins: {
      vue: eslintPluginVue,
    },
    rules: {
      // Vue 相关规则
      'vue/multi-word-component-names': 'off',
      'vue/no-multiple-template-root': 'off',
      'vue/require-default-prop': 'off',
      
      // JavaScript 规则
      'prefer-const': 'error',
      'no-var': 'error',
      'no-console': 'off',
      'no-unused-vars': 'warn',
      'no-undef': 'error',
      'comma-dangle': ['error', 'only-multiline'],
      'quotes': ['error', 'single', { 'allowTemplateLiterals': true }],
      'semi': ['error', 'never'],
      'indent': ['error', 2],
    }
  }
];
