const fs = require('fs');

let file = '/Volumes/data/DEV2/xiaozhi-ce/backend/src/app/ai/providers/schema_registry.py';
let content = fs.readFileSync(file, 'utf8');

const geminiLiveSchema = `
LLM_GEMINI_LIVE_SCHEMA = ProviderTypeSchema(
    label="Gemini Live (Voice-to-Voice)",
    description="Sử dụng Gemini Multimodal Live API (BidiGenerateContent). Hỗ trợ nhận diện giọng nói và trả về giọng nói theo thời gian thực với độ trễ cực thấp.",
    fields=[
        ProviderFieldSchema(
            name="api_key",
            label="API Key",
            type=FieldType.SECRET,
            required=True,
            description="Lấy API Key MIỄN PHÍ tại: https://aistudio.google.com/app/apikey",
        ),
        ProviderFieldSchema(
            name="model_name",
            label="Model",
            type=FieldType.STRING,
            required=True,
            default="gemini-2.0-flash-exp",
            placeholder="gemini-2.0-flash-exp hoặc gemini-2.5-flash",
            description="Model hỗ trợ BidiGenerateContent",
        ),
        ProviderFieldSchema(
            name="voice_name",
            label="Voice",
            type=FieldType.SELECT,
            required=False,
            default="Aoede",
            options=[
                SelectOption(value="Puck", label="Puck (Nam)"),
                SelectOption(value="Charon", label="Charon (Nam)"),
                SelectOption(value="Kore", label="Kore (Nữ)"),
                SelectOption(value="Fenrir", label="Fenrir (Nam)"),
                SelectOption(value="Aoede", label="Aoede (Nữ)"),
            ],
            description="Giọng nói của Gemini",
        ),
    ],
)
`;

// Insert the new schema right after LLM_GEMINI_SCHEMA
if (!content.includes('LLM_GEMINI_LIVE_SCHEMA')) {
    content = content.replace(
        /LLM_VLLM_SCHEMA = ProviderTypeSchema\(/,
        geminiLiveSchema + '\n\nLLM_VLLM_SCHEMA = ProviderTypeSchema('
    );
    
    // Also add to ALL_PROVIDER_SCHEMAS dictionary
    content = content.replace(
        /"gemini": LLM_GEMINI_SCHEMA,/,
        `"gemini": LLM_GEMINI_SCHEMA,
        "gemini_live": LLM_GEMINI_LIVE_SCHEMA,`
    );
    
    fs.writeFileSync(file, content);
    console.log("Updated schema_registry.py");
} else {
    console.log("LLM_GEMINI_LIVE_SCHEMA already exists");
}
