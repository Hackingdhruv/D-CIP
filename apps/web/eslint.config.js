import react from '@dcip/config/eslint/react';

export default [
  ...react,
  {
    settings: { react: { version: 'detect' } },
  },
];
