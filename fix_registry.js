const fs = require('fs');

let file = '/Volumes/data/DEV2/xiaozhi-ce/backend/src/app/ai/providers/schema_registry.py';
let content = fs.readFileSync(file, 'utf8');

content = content.replace(
    /description="Gemini API key từ Google AI Studio",/g,
    `description="Lấy API Key MIỄN PHÍ tại: https://aistudio.google.com/app/apikey",`
);

fs.writeFileSync(file, content);

