"""
Emotion Detection Service

Detects user emotions from text and audio for adaptive AI responses.
"""

import re
from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum

from ..core.logger import get_logger

logger = get_logger(__name__)


class Emotion(str, Enum):
    """Supported emotion categories"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    TIRED = "tired"
    EXCITED = "excited"
    CONFUSED = "confused"
    GRATEFUL = "grateful"


@dataclass
class EmotionResult:
    """Result of emotion detection"""
    emotion: Emotion
    confidence: float
    scores: dict[str, float]
    source: str  # "text", "audio", "combined"
    

# Vietnamese emotion keywords
EMOTION_KEYWORDS: dict[Emotion, list[str]] = {
    Emotion.HAPPY: [
        "vui", "vui vẻ", "hạnh phúc", "sung sướng", "tuyệt vời", "tuyệt", 
        "hay quá", "tốt quá", "thích quá", "yêu", "thương", "cảm ơn",
        "haha", "hihi", "hehe", ":)", "😀", "😊", "🥰", "❤️",
        "xuất sắc", "hoàn hảo", "đỉnh", "phê",
    ],
    Emotion.SAD: [
        "buồn", "buồn quá", "đau", "khóc", "nước mắt", "thất vọng",
        "chán", "chán quá", "tệ", "thất bại", "không vui", "u sầu",
        "nhớ", "cô đơn", "một mình", ":(", "😢", "😭", "💔",
        "tiếc", "hối hận", "đáng tiếc",
    ],
    Emotion.ANGRY: [
        "giận", "tức", "bực", "khó chịu", "điên", "điên tiết",
        "ghét", "chán ghét", "cáu", "nổi điên", "ức", "tức giận",
        "đ**", "dm", "vl", "wtf", "😠", "😡", "🤬",
        "không chấp nhận", "quá đáng", "vô lý",
    ],
    Emotion.ANXIOUS: [
        "lo", "lo lắng", "sợ", "lo sợ", "hoang mang", "bất an",
        "hồi hộp", "căng thẳng", "áp lực", "stress", "đau đầu",
        "không biết", "làm sao", "thế nào", "😰", "😨", "😱",
        "run", "hoảng", "hoảng sợ",
    ],
    Emotion.TIRED: [
        "mệt", "mệt mỏi", "kiệt sức", "chán", "buồn ngủ", "ngủ",
        "nghỉ", "thở", "không muốn", "uể oải", "lười", "đuối",
        "😴", "🥱", "😩", "đừng", "thôi", "để sau",
    ],
    Emotion.EXCITED: [
        "excited", "háo hức", "nóng lòng", "sốt sắng", "hồi hộp",
        "không chờ được", "muốn", "rất muốn", "wow", "ôi",
        "thật sao", "thật à", "🎉", "🥳", "✨", "💫",
        "tuyệt vời", "phi thường", "kinh ngạc",
    ],
    Emotion.CONFUSED: [
        "không hiểu", "hả", "gì", "sao", "tại sao", "như thế nào",
        "confused", "bối rối", "lúng túng", "khó hiểu", "ơ",
        "🤔", "😕", "❓", "??", "lạ", "kỳ lạ",
    ],
    Emotion.GRATEFUL: [
        "cảm ơn", "biết ơn", "cám ơn", "thank", "thanks", "tks",
        "may mắn", "hạnh phúc", "🙏", "💕", "tuyệt vời",
        "giúp đỡ", "hữu ích", "bạn giỏi",
    ],
}

# Emotion response prompts for LLM
EMOTION_PROMPTS: dict[Emotion, str] = {
    Emotion.NEUTRAL: "",
    Emotion.HAPPY: "Người dùng đang vui vẻ. Hãy chia sẻ niềm vui và duy trì năng lượng tích cực.",
    Emotion.SAD: "Người dùng có vẻ buồn. Hãy phản hồi với sự đồng cảm, ấm áp và nhẹ nhàng.",
    Emotion.ANGRY: "Người dùng đang bực bội. Hãy bình tĩnh, kiên nhẫn và tập trung vào giải quyết vấn đề.",
    Emotion.ANXIOUS: "Người dùng có vẻ lo lắng. Hãy trấn an, đưa ra thông tin rõ ràng và hỗ trợ.",
    Emotion.TIRED: "Người dùng có vẻ mệt. Hãy phản hồi ngắn gọn, hữu ích và thông cảm.",
    Emotion.EXCITED: "Người dùng đang hào hứng! Hãy chia sẻ sự phấn khích và khuyến khích họ.",
    Emotion.CONFUSED: "Người dùng có vẻ bối rối. Hãy giải thích rõ ràng, đơn giản và kiên nhẫn.",
    Emotion.GRATEFUL: "Người dùng đang biết ơn. Hãy đón nhận lời cảm ơn một cách khiêm tốn.",
}


class EmotionDetector:
    """
    Detects emotions from text input.
    
    Uses keyword matching and pattern analysis. 
    Can be extended with ML models for more accuracy.
    """
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for emotion detection"""
        self._patterns: dict[Emotion, list[re.Pattern]] = {}
        
        for emotion, keywords in EMOTION_KEYWORDS.items():
            patterns = []
            for kw in keywords:
                # Escape special regex characters
                escaped = re.escape(kw)
                # Create word boundary pattern
                pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
                patterns.append(pattern)
            self._patterns[emotion] = patterns
    
    def detect_from_text(self, text: str) -> EmotionResult:
        """
        Detect emotion from text using keyword matching.
        
        Args:
            text: User message text
            
        Returns:
            EmotionResult with detected emotion and confidence
        """
        text_lower = text.lower()
        scores: dict[str, float] = {e.value: 0.0 for e in Emotion}
        
        # Score each emotion based on keyword matches
        total_matches = 0
        for emotion, patterns in self._patterns.items():
            for pattern in patterns:
                matches = len(pattern.findall(text_lower))
                if matches > 0:
                    scores[emotion.value] += matches
                    total_matches += matches
        
        # Normalize scores
        if total_matches > 0:
            for emotion in scores:
                scores[emotion] /= total_matches
        
        # Determine dominant emotion
        if total_matches == 0:
            # No emotion keywords found
            return EmotionResult(
                emotion=Emotion.NEUTRAL,
                confidence=0.5,
                scores=scores,
                source="text"
            )
        
        # Find highest scoring emotion
        dominant = max(scores, key=scores.get)
        confidence = scores[dominant]
        
        # Boost confidence based on match count
        confidence = min(confidence + (total_matches * 0.1), 1.0)
        
        return EmotionResult(
            emotion=Emotion(dominant),
            confidence=round(confidence, 2),
            scores={k: round(v, 2) for k, v in scores.items()},
            source="text"
        )
    
    def detect_from_audio_features(
        self,
        pitch_mean: float,
        pitch_std: float,
        energy_mean: float,
        speech_rate: float
    ) -> EmotionResult:
        """
        Detect emotion from audio features.
        
        This is a simplified heuristic-based approach.
        For production, use a trained ML model.
        
        Args:
            pitch_mean: Average pitch in Hz
            pitch_std: Pitch standard deviation
            energy_mean: Average energy/volume
            speech_rate: Words per second
            
        Returns:
            EmotionResult
        """
        scores: dict[str, float] = {e.value: 0.1 for e in Emotion}
        
        # High pitch + high energy + fast = excited/angry
        if pitch_mean > 200 and energy_mean > 0.7:
            if speech_rate > 3.5:
                scores[Emotion.EXCITED.value] = 0.7
                scores[Emotion.ANGRY.value] = 0.5
            else:
                scores[Emotion.HAPPY.value] = 0.6
        
        # Low pitch + low energy + slow = sad/tired
        elif pitch_mean < 150 and energy_mean < 0.4:
            if speech_rate < 2.0:
                scores[Emotion.SAD.value] = 0.6
                scores[Emotion.TIRED.value] = 0.5
            else:
                scores[Emotion.NEUTRAL.value] = 0.5
        
        # High pitch variation = anxious
        if pitch_std > 50:
            scores[Emotion.ANXIOUS.value] += 0.3
        
        # Normalize
        total = sum(scores.values())
        scores = {k: v/total for k, v in scores.items()}
        
        dominant = max(scores, key=scores.get)
        
        return EmotionResult(
            emotion=Emotion(dominant),
            confidence=round(scores[dominant], 2),
            scores={k: round(v, 2) for k, v in scores.items()},
            source="audio"
        )
    
    def combine_results(
        self,
        text_result: EmotionResult,
        audio_result: Optional[EmotionResult] = None
    ) -> EmotionResult:
        """
        Combine text and audio emotion results.
        
        Uses weighted average with text having higher weight
        since it's more reliable for this use case.
        """
        if audio_result is None:
            return text_result
        
        # Weight: 70% text, 30% audio
        text_weight = 0.7
        audio_weight = 0.3
        
        combined_scores: dict[str, float] = {}
        for emotion in Emotion:
            text_score = text_result.scores.get(emotion.value, 0)
            audio_score = audio_result.scores.get(emotion.value, 0)
            combined_scores[emotion.value] = (
                text_score * text_weight + audio_score * audio_weight
            )
        
        dominant = max(combined_scores, key=combined_scores.get)
        confidence = (
            text_result.confidence * text_weight + 
            audio_result.confidence * audio_weight
        )
        
        return EmotionResult(
            emotion=Emotion(dominant),
            confidence=round(confidence, 2),
            scores={k: round(v, 2) for k, v in combined_scores.items()},
            source="combined"
        )


class EmotionalResponseAdapter:
    """
    Adapts AI responses based on detected emotion.
    """
    
    @staticmethod
    def adapt_prompt(
        base_prompt: str,
        emotion: Emotion,
        include_context: bool = True
    ) -> str:
        """
        Inject emotional context into the system prompt.
        
        Args:
            base_prompt: Original system prompt
            emotion: Detected user emotion
            include_context: Whether to include emotion context
            
        Returns:
            Enhanced prompt with emotion awareness
        """
        if not include_context or emotion == Emotion.NEUTRAL:
            return base_prompt
        
        emotion_prompt = EMOTION_PROMPTS.get(emotion, "")
        if not emotion_prompt:
            return base_prompt
        
        return f"{base_prompt}\n\n[Ngữ cảnh cảm xúc]: {emotion_prompt}"
    
    @staticmethod
    def get_voice_params(emotion: Emotion) -> dict[str, Any]:
        """
        Get TTS voice parameters based on emotion.
        
        Returns parameters that can adjust voice tone/speed.
        """
        params = {
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%",
        }
        
        if emotion == Emotion.HAPPY:
            params["rate"] = "+5%"
            params["pitch"] = "+5Hz"
        elif emotion == Emotion.SAD:
            params["rate"] = "-10%"
            params["pitch"] = "-5Hz"
        elif emotion == Emotion.EXCITED:
            params["rate"] = "+10%"
            params["pitch"] = "+10Hz"
        elif emotion == Emotion.TIRED:
            params["rate"] = "-5%"
            params["volume"] = "-5%"
        elif emotion == Emotion.ANGRY:
            params["rate"] = "+5%"
        
        return params
    
    @staticmethod
    def should_check_wellbeing(
        recent_emotions: list[Emotion],
        threshold: float = 0.5
    ) -> bool:
        """
        Determine if AI should proactively check on user's wellbeing.
        
        Returns True if recent emotions are predominantly negative.
        """
        if len(recent_emotions) < 3:
            return False
        
        negative_emotions = {Emotion.SAD, Emotion.ANGRY, Emotion.ANXIOUS, Emotion.TIRED}
        negative_count = sum(1 for e in recent_emotions if e in negative_emotions)
        
        return (negative_count / len(recent_emotions)) > threshold


# Singleton instance
_emotion_detector: Optional[EmotionDetector] = None


def get_emotion_detector() -> EmotionDetector:
    """Get the emotion detector singleton"""
    global _emotion_detector
    if _emotion_detector is None:
        _emotion_detector = EmotionDetector()
    return _emotion_detector
