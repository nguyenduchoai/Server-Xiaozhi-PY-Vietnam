const fs = require('fs');

// Fix axios-instance.ts
let axiosFile = '/Volumes/data/DEV2/xiaozhi-ce/frontend/src/config/axios-instance.ts';
let axiosContent = fs.readFileSync(axiosFile, 'utf8');

axiosContent = axiosContent.replace(
    /\/\/ Redirect to login page\s*window\.location\.href = "\/login";/,
    '// Redirect is handled by ProtectedRoute component when isAuthenticated becomes false'
);

fs.writeFileSync(axiosFile, axiosContent);

// Fix user-queries.ts
let queriesFile = '/Volumes/data/DEV2/xiaozhi-ce/frontend/src/queries/user-queries.ts';
let queriesContent = fs.readFileSync(queriesFile, 'utf8');

queriesContent = queriesContent.replace(
    /retry: 1,/,
    `retry: (failureCount, error: any) => {
      if (error?.response?.status === 401 || error?.response?.status === 403) return false;
      return failureCount < 1;
    },`
);

fs.writeFileSync(queriesFile, queriesContent);

