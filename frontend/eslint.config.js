import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'

export default [
    { ignores: ['dist/**', '../static/dist/**', 'node_modules/**'] },
    js.configs.recommended,
    {
        files: ['**/*.{js,jsx}'],
        languageOptions: {
            ecmaVersion: 'latest',
            sourceType: 'module',
            globals: { ...globals.browser, ...globals.node },
            parserOptions: { ecmaFeatures: { jsx: true } },
        },
        plugins: { react, 'react-hooks': reactHooks },
        settings: { react: { version: 'detect' } },
        rules: {
            // Without these, every component imported for use in JSX reads as
            // an unused variable — JSX identifiers aren't usage to core ESLint.
            'react/jsx-uses-react': 'error',
            'react/jsx-uses-vars': 'error',
            ...reactHooks.configs.recommended.rules,
            // Catches exactly the class of bug fixed in useNotifications:
            // a callback closing over state that should have been a ref.
            'react-hooks/exhaustive-deps': 'warn',
            'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
            // `try { ... } catch {}` is a deliberate idiom here for optional
            // work (localStorage, clipboard) that must never break a render.
            'no-empty': ['error', { allowEmptyCatch: true }],
        },
    },
    {
        files: ['**/__tests__/**', '**/*.test.{js,jsx}', 'src/test-setup.js'],
        languageOptions: { globals: { ...globals.vitest, ...globals.node } },
    },
]
