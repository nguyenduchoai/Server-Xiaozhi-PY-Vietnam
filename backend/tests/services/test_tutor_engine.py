"""
Unit Tests for AI Tutor - MicroKnowledge Module

Tests cover:
- MicroKnowledge model methods
- TutorEngine mastery calculation
- TutorEngine session management
- MKGenerator content generation
- CRUD operations

Run with: pytest tests/services/test_tutor_engine.py -v
"""

from datetime import datetime, timedelta


# =============================================================================
# MASTERY CALCULATION TESTS
# =============================================================================

class TestMasteryState:
    """Test MasteryState dataclass and calculation."""
    
    def test_mastery_score_calculation(self):
        """TC-020: Verify mastery score formula."""
        from app.services.tutor_engine import MasteryState
        
        state = MasteryState(
            mk_id="test_mk",
            accuracy=0.8,
            avg_response_time_ms=1500,
            consistency=0.9,
            recent_improvement=0.1,
            reviews=5,
            correct=4,
        )
        
        # mastery = accuracy*0.5 + time*0.2 + consistency*0.2 + improvement*0.1
        # time_score = min(1.0, 2000/1500) = 1.0 (capped)
        # = 0.8*0.5 + 1.0*0.2 + 0.9*0.2 + 0.1*0.1
        # = 0.4 + 0.2 + 0.18 + 0.01 = 0.79
        
        assert 0.75 <= state.mastery_score <= 0.85
    
    def test_mastery_score_poor_time(self):
        """Test mastery with slow response time."""
        from app.services.tutor_engine import MasteryState
        
        state = MasteryState(
            mk_id="test_mk",
            accuracy=1.0,
            avg_response_time_ms=5000,  # Very slow
            consistency=1.0,
            recent_improvement=0.0,
            reviews=5,
            correct=5,
        )
        
        # time_score = min(1.0, 2000/5000) = 0.4
        # = 1.0*0.5 + 0.4*0.2 + 1.0*0.2 + 0.0*0.1
        # = 0.5 + 0.08 + 0.2 + 0 = 0.78
        
        assert 0.7 <= state.mastery_score <= 0.85
    
    def test_mastery_status_weak(self):
        """TC-021a: Test weak status threshold."""
        from app.services.tutor_engine import MasteryState, MasteryStatus
        
        state = MasteryState(
            mk_id="test_mk",
            accuracy=0.2,
            consistency=0.2,
            recent_improvement=0.0,
            reviews=3,
            correct=1,
        )
        
        assert state.status == MasteryStatus.WEAK
    
    def test_mastery_status_forming(self):
        """TC-021b: Test forming status threshold."""
        from app.services.tutor_engine import MasteryState, MasteryStatus
        
        state = MasteryState(
            mk_id="test_mk",
            accuracy=0.6,
            avg_response_time_ms=2000,
            consistency=0.6,
            recent_improvement=0.0,
            reviews=4,
            correct=3,
        )
        
        assert state.status == MasteryStatus.FORMING
    
    def test_mastery_status_strong(self):
        """TC-021c: Test strong status threshold."""
        from app.services.tutor_engine import MasteryState, MasteryStatus
        
        state = MasteryState(
            mk_id="test_mk",
            accuracy=0.9,
            avg_response_time_ms=1500,
            consistency=0.9,
            recent_improvement=0.1,
            reviews=4,
            correct=4,
        )
        
        assert state.status == MasteryStatus.STRONG
    
    def test_mastery_status_mastered(self):
        """TC-021d: Test mastered status (requires 5+ reviews)."""
        from app.services.tutor_engine import MasteryState, MasteryStatus
        
        state = MasteryState(
            mk_id="test_mk",
            accuracy=0.95,
            avg_response_time_ms=1000,
            consistency=1.0,
            recent_improvement=0.05,
            reviews=10,
            correct=10,
        )
        
        assert state.status == MasteryStatus.MASTERED
    
    def test_is_due_no_next_review(self):
        """Test is_due when next_review is None."""
        from app.services.tutor_engine import MasteryState
        
        state = MasteryState(mk_id="test_mk", next_review=None)
        assert state.is_due is True
    
    def test_is_due_past(self):
        """Test is_due when next_review is in past."""
        from app.services.tutor_engine import MasteryState
        
        state = MasteryState(
            mk_id="test_mk",
            next_review=datetime.utcnow() - timedelta(days=1)
        )
        assert state.is_due is True
    
    def test_is_due_future(self):
        """Test is_due when next_review is in future."""
        from app.services.tutor_engine import MasteryState
        
        state = MasteryState(
            mk_id="test_mk",
            next_review=datetime.utcnow() + timedelta(days=1)
        )
        assert state.is_due is False


# =============================================================================
# TUTOR SESSION TESTS
# =============================================================================

class TestTutorSession:
    """Test TutorSession class."""
    
    def test_session_elapsed_time(self):
        """Test elapsed time calculation."""
        from app.services.tutor_engine import TutorSession
        
        session = TutorSession(
            session_id="test_session",
            user_id="user_123",
            started_at=datetime.utcnow() - timedelta(seconds=30),
            duration_limit_seconds=120,
        )
        
        assert 29 <= session.elapsed_seconds <= 32
        assert 88 <= session.remaining_seconds <= 91
    
    def test_session_expired(self):
        """TC-004: Test session expiration."""
        from app.services.tutor_engine import TutorSession
        
        session = TutorSession(
            session_id="test_session",
            user_id="user_123",
            started_at=datetime.utcnow() - timedelta(seconds=150),
            duration_limit_seconds=120,
        )
        
        assert session.is_expired is True
    
    def test_session_not_expired(self):
        """Test session is not expired."""
        from app.services.tutor_engine import TutorSession
        
        session = TutorSession(
            session_id="test_session",
            user_id="user_123",
            started_at=datetime.utcnow() - timedelta(seconds=30),
            duration_limit_seconds=120,
        )
        
        assert session.is_expired is False
    
    def test_session_accuracy_calculation(self):
        """Test session accuracy calculation."""
        from app.services.tutor_engine import TutorSession
        
        session = TutorSession(
            session_id="test_session",
            user_id="user_123",
            started_at=datetime.utcnow(),
            duration_limit_seconds=120,
            interactions=[
                {"correct": True, "response_time_ms": 1000},
                {"correct": True, "response_time_ms": 1200},
                {"correct": False, "response_time_ms": 2000},
                {"correct": True, "response_time_ms": 1500},
            ]
        )
        
        assert session.accuracy == 0.75  # 3/4 correct
    
    def test_session_stats(self):
        """Test session statistics generation."""
        from app.services.tutor_engine import TutorSession
        
        session = TutorSession(
            session_id="test_session",
            user_id="user_123",
            started_at=datetime.utcnow() - timedelta(seconds=60),
            duration_limit_seconds=120,
            subject="english",
            topic="food",
            interactions=[
                {"correct": True, "response_time_ms": 1000},
                {"correct": True, "response_time_ms": 1500},
            ]
        )
        
        stats = session.to_stats()
        
        assert stats["mk_reviewed"] == 2
        assert stats["accuracy"] == 100.0
        assert stats["subject"] == "english"
        assert stats["topic"] == "food"


# =============================================================================
# MK MODEL TESTS
# =============================================================================

class TestMicroKnowledgeModel:
    """Test MicroKnowledge model methods."""
    
    def test_check_answer_exact_match(self):
        """Test exact answer matching."""
        from app.models.education.micro_knowledge import MicroKnowledge
        
        mk = MicroKnowledge()
        mk.interaction = {"expected_answer": ["apple", "an apple"]}
        
        assert mk.check_answer("apple") is True
        assert mk.check_answer("Apple") is True  # Case insensitive
        assert mk.check_answer("an apple") is True
    
    def test_check_answer_partial_match(self):
        """Test partial/contains matching."""
        from app.models.education.micro_knowledge import MicroKnowledge
        
        mk = MicroKnowledge()
        mk.interaction = {"expected_answer": ["apple"]}
        
        # "apples" contains "apple"
        assert mk.check_answer("apples") is True
    
    def test_check_answer_wrong(self):
        """Test wrong answer."""
        from app.models.education.micro_knowledge import MicroKnowledge
        
        mk = MicroKnowledge()
        mk.interaction = {"expected_answer": ["apple"]}
        
        assert mk.check_answer("orange") is False
        assert mk.check_answer("banana") is False
    
    def test_check_answer_empty(self):
        """EC-03: Test empty answer."""
        from app.models.education.micro_knowledge import MicroKnowledge
        
        mk = MicroKnowledge()
        mk.interaction = {"expected_answer": ["apple"]}
        
        assert mk.check_answer("") is False
        assert mk.check_answer(None) is False
    
    def test_to_voice_format(self):
        """Test voice format conversion."""
        from app.models.education.micro_knowledge import MicroKnowledge
        
        mk = MicroKnowledge()
        mk.mk_id = "eng_food_apple"
        mk.content = {
            "text": "Apple",
            "phonetic": "/ˈæp.əl/",
            "meaning_vi": "Quả táo",
            "audio": "https://example.com/apple.mp3"
        }
        mk.interaction = {
            "question": "What is this?",
            "hints": ["Red fruit"]
        }
        
        voice = mk.to_voice_format()
        
        assert voice["mk_id"] == "eng_food_apple"
        assert voice["text"] == "Apple"
        assert voice["phonetic"] == "/ˈæp.əl/"
        assert voice["question"] == "What is this?"
        assert "Red fruit" in voice["hints"]


# =============================================================================
# MK GENERATOR TESTS
# =============================================================================

class TestMKGenerator:
    """Test MKGenerator service."""
    
    def test_generate_from_vocabulary(self):
        """TC-030: Test MK generation from vocabulary."""
        from app.services.mk_generator import MKGenerator
        
        generator = MKGenerator()
        
        # Mock vocabulary
        class MockVocab:
            id = "vocab_123"
            word = "hello"
            meaning_vi = "Xin chào"
            meaning_en = "A greeting"
            pronunciation = "/həˈloʊ/"
            examples = [{"en": "Hello!", "vi": "Xin chào!"}]
            level = "A1"
            topic = "greetings"
            category = "common"
            word_type = "noun"
            image_url = None
            audio_url = None
        
        vocab = MockVocab()
        result = generator.generate_from_vocabulary(vocab)
        
        assert result["mk_id"] == "eng_greetings_hello"
        assert result["subject"] == "english"
        assert result["topic"] == "greetings"
        assert result["difficulty"] == 1  # A1 -> 1
        assert result["content"]["text"] == "hello"
        assert result["content"]["meaning_vi"] == "Xin chào"
        assert "hello" in result["interaction"]["expected_answer"]
        assert result["source_vocabulary_id"] == "vocab_123"
    
    def test_cefr_to_difficulty_mapping(self):
        """Test CEFR to difficulty conversion."""
        from app.services.mk_generator import MKGenerator
        
        assert MKGenerator.CEFR_TO_DIFFICULTY["A1"] == 1
        assert MKGenerator.CEFR_TO_DIFFICULTY["A2"] == 2
        assert MKGenerator.CEFR_TO_DIFFICULTY["B1"] == 3
        assert MKGenerator.CEFR_TO_DIFFICULTY["B2"] == 4
        assert MKGenerator.CEFR_TO_DIFFICULTY["C1"] == 5
    
    def test_build_expected_answers_with_article(self):
        """Test answer variations with articles."""
        from app.services.mk_generator import MKGenerator
        
        generator = MKGenerator()
        answers = generator._build_expected_answers("apple")
        
        assert "apple" in answers
        assert "an apple" in answers  # Vowel -> "an"
    
    def test_build_hints(self):
        """Test hint generation."""
        from app.services.mk_generator import MKGenerator
        
        generator = MKGenerator()
        
        class MockVocab:
            word = "Apple"
            word_type = "noun"
            category = "food"
            examples = [{"vi": "Tôi ăn táo"}]
            topic = "fruits"
        
        hints = generator._build_hints(MockVocab())
        
        assert len(hints) <= 3
        assert any("A" in h for h in hints)  # First letter hint


# =============================================================================
# SAMPLE DATA TESTS
# =============================================================================

class TestSampleData:
    """Test sample MK data structure."""
    
    def test_sample_mk_structure(self):
        """TC-031: Verify sample MK data structure."""
        from app.services.mk_generator import SAMPLE_MICRO_KNOWLEDGE
        
        assert len(SAMPLE_MICRO_KNOWLEDGE) == 5
        
        for mk in SAMPLE_MICRO_KNOWLEDGE:
            assert "mk_id" in mk
            assert "subject" in mk
            assert "topic" in mk
            assert "content" in mk
            assert "interaction" in mk
            assert "text" in mk["content"]
            assert "expected_answer" in mk["interaction"]
    
    def test_sample_mk_apple(self):
        """Test apple sample data."""
        from app.services.mk_generator import SAMPLE_MICRO_KNOWLEDGE
        
        apple_mk = next((m for m in SAMPLE_MICRO_KNOWLEDGE if m["mk_id"] == "eng_food_apple"), None)
        
        assert apple_mk is not None
        assert apple_mk["content"]["text"] == "Apple"
        assert apple_mk["content"]["meaning_vi"] == "Quả táo"
        assert "apple" in apple_mk["interaction"]["expected_answer"]


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_interactions(self):
        """Test session with no interactions."""
        from app.services.tutor_engine import TutorSession
        
        session = TutorSession(
            session_id="test",
            user_id="user",
            started_at=datetime.utcnow(),
            duration_limit_seconds=120,
        )
        
        assert session.accuracy == 0.0
        assert session.avg_response_time_ms == 2000
    
    def test_serialization_round_trip(self):
        """Test mastery state serialization."""
        from app.services.tutor_engine import MasteryState
        
        original = MasteryState(
            mk_id="test_mk",
            accuracy=0.8,
            reviews=5,
            correct=4,
            last_seen=datetime.utcnow(),
            next_review=datetime.utcnow() + timedelta(days=3),
        )
        
        data = original.to_dict()
        restored = MasteryState.from_dict(data)
        
        assert restored.mk_id == original.mk_id
        assert restored.accuracy == original.accuracy
        assert restored.reviews == original.reviews
