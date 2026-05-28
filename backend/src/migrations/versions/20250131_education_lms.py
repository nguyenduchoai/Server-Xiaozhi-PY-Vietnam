"""
Education LMS Module - Database Migration

Creates tables for:
- edu_course: Courses
- edu_lesson: Lessons within courses
- edu_quiz: Quizzes
- edu_question: Quiz questions
- edu_flashcard_deck: Flashcard decks
- edu_flashcard: Individual flashcards
- edu_enrollment: Course enrollments
- edu_lesson_progress: Lesson progress tracking
- edu_quiz_submission: Quiz results
- edu_flashcard_review: Spaced repetition state
- edu_achievement: Achievement definitions
- edu_user_achievement: User earned achievements
- edu_user_stats: Aggregated user statistics
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20250131_education_lms'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create edu_course table
    op.create_table(
        'edu_course',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('cover_image', sa.String(500)),
        sa.Column('target_audience', sa.String(100)),
        sa.Column('difficulty', sa.String(20), default='beginner'),
        sa.Column('estimated_hours', sa.Integer, default=0),
        sa.Column('is_published', sa.Boolean, default=False, index=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create edu_lesson table
    op.create_table(
        'edu_lesson',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('course_id', sa.String(36), sa.ForeignKey('edu_course.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('lesson_order', sa.Integer, default=0, index=True),
        sa.Column('lesson_type', sa.String(20), nullable=False),
        sa.Column('content', postgresql.JSONB, default={}),
        sa.Column('duration_minutes', sa.Integer, default=10),
        sa.Column('objectives', postgresql.ARRAY(sa.Text)),
        sa.Column('is_published', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create edu_quiz table
    op.create_table(
        'edu_quiz',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('lesson_id', sa.String(36), sa.ForeignKey('edu_lesson.id', ondelete='CASCADE'), index=True),
        sa.Column('course_id', sa.String(36), sa.ForeignKey('edu_course.id', ondelete='CASCADE'), index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('passing_score', sa.Integer, default=70),
        sa.Column('time_limit_seconds', sa.Integer),
        sa.Column('shuffle_questions', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create edu_question table
    op.create_table(
        'edu_question',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('quiz_id', sa.String(36), sa.ForeignKey('edu_quiz.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('question_text', sa.Text, nullable=False),
        sa.Column('question_type', sa.String(20), nullable=False),
        sa.Column('options', postgresql.JSONB),
        sa.Column('correct_answer', sa.Text, nullable=False),
        sa.Column('explanation', sa.Text),
        sa.Column('points', sa.Integer, default=10),
        sa.Column('question_order', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create edu_flashcard_deck table
    op.create_table(
        'edu_flashcard_deck',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('lesson_id', sa.String(36), sa.ForeignKey('edu_lesson.id', ondelete='CASCADE'), index=True),
        sa.Column('course_id', sa.String(36), sa.ForeignKey('edu_course.id', ondelete='CASCADE'), index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(100)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create edu_flashcard table
    op.create_table(
        'edu_flashcard',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('deck_id', sa.String(36), sa.ForeignKey('edu_flashcard_deck.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('front', sa.Text, nullable=False),
        sa.Column('back', sa.Text, nullable=False),
        sa.Column('pronunciation', sa.String(100)),
        sa.Column('example_sentence', sa.Text),
        sa.Column('image_url', sa.String(500)),
        sa.Column('audio_url', sa.String(500)),
        sa.Column('difficulty', sa.Integer, default=1),
        sa.Column('card_order', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create edu_enrollment table
    op.create_table(
        'edu_enrollment',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('course_id', sa.String(36), sa.ForeignKey('edu_course.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('enrolled_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime),
        sa.UniqueConstraint('user_id', 'course_id', name='uq_user_course_enrollment'),
    )
    
    # Create edu_lesson_progress table
    op.create_table(
        'edu_lesson_progress',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('lesson_id', sa.String(36), sa.ForeignKey('edu_lesson.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('status', sa.String(20), default='not_started'),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('score', sa.Integer),
        sa.Column('time_spent_seconds', sa.Integer, default=0),
        sa.Column('attempts', sa.Integer, default=0),
        sa.UniqueConstraint('user_id', 'lesson_id', name='uq_user_lesson_progress'),
    )
    
    # Create edu_quiz_submission table
    op.create_table(
        'edu_quiz_submission',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('quiz_id', sa.String(36), sa.ForeignKey('edu_quiz.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('score', sa.Integer, nullable=False),
        sa.Column('total_points', sa.Integer, nullable=False),
        sa.Column('percentage', sa.Numeric(5, 2), nullable=False),
        sa.Column('passed', sa.Boolean, nullable=False),
        sa.Column('answers', postgresql.JSONB, nullable=False),
        sa.Column('time_taken_seconds', sa.Integer),
        sa.Column('submitted_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create edu_flashcard_review table
    op.create_table(
        'edu_flashcard_review',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('card_id', sa.String(36), sa.ForeignKey('edu_flashcard.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ease_factor', sa.Numeric(4, 2), default=2.5),
        sa.Column('interval_days', sa.Integer, default=1),
        sa.Column('repetitions', sa.Integer, default=0),
        sa.Column('last_reviewed_at', sa.DateTime),
        sa.Column('next_review_at', sa.DateTime, index=True),
        sa.UniqueConstraint('user_id', 'card_id', name='uq_user_card_review'),
    )
    
    # Create edu_achievement table
    op.create_table(
        'edu_achievement',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('icon', sa.String(50)),
        sa.Column('points', sa.Integer, default=0),
        sa.Column('criteria', postgresql.JSONB, nullable=False),
    )
    
    # Create edu_user_achievement table
    op.create_table(
        'edu_user_achievement',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('achievement_id', sa.String(36), sa.ForeignKey('edu_achievement.id', ondelete='CASCADE'), nullable=False),
        sa.Column('earned_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),
    )
    
    # Create edu_user_stats table
    op.create_table(
        'edu_user_stats',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('total_points', sa.Integer, default=0),
        sa.Column('current_streak', sa.Integer, default=0),
        sa.Column('longest_streak', sa.Integer, default=0),
        sa.Column('lessons_completed', sa.Integer, default=0),
        sa.Column('quizzes_passed', sa.Integer, default=0),
        sa.Column('cards_mastered', sa.Integer, default=0),
        sa.Column('last_activity_date', sa.Date),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Seed default achievements
    op.execute("""
        INSERT INTO edu_achievement (id, code, name, description, icon, points, criteria) VALUES
        ('ach-001', 'first_lesson', 'First Steps', 'Complete your first lesson', '🎯', 10, '{"lessons_completed": 1}'),
        ('ach-002', 'streak_3', 'Getting Started', 'Learn 3 days in a row', '🔥', 30, '{"streak_days": 3}'),
        ('ach-003', 'streak_7', 'On Fire', 'Learn 7 days in a row', '🔥🔥', 70, '{"streak_days": 7}'),
        ('ach-004', 'streak_30', 'Dedicated Learner', 'Learn 30 days in a row', '🏆', 300, '{"streak_days": 30}'),
        ('ach-005', 'quiz_master', 'Quiz Master', 'Score 100% on any quiz', '🧠', 50, '{"perfect_quiz": true}'),
        ('ach-006', 'vocab_50', 'Word Builder', 'Learn 50 flashcards', '📚', 50, '{"cards_mastered": 50}'),
        ('ach-007', 'vocab_100', 'Word Collector', 'Learn 100 flashcards', '📖', 100, '{"cards_mastered": 100}'),
        ('ach-008', 'course_complete', 'Course Champion', 'Complete your first course', '🎓', 200, '{"courses_completed": 1}')
        ON CONFLICT (code) DO NOTHING;
    """)


def downgrade():
    op.drop_table('edu_user_stats')
    op.drop_table('edu_user_achievement')
    op.drop_table('edu_achievement')
    op.drop_table('edu_flashcard_review')
    op.drop_table('edu_quiz_submission')
    op.drop_table('edu_lesson_progress')
    op.drop_table('edu_enrollment')
    op.drop_table('edu_flashcard')
    op.drop_table('edu_flashcard_deck')
    op.drop_table('edu_question')
    op.drop_table('edu_quiz')
    op.drop_table('edu_lesson')
    op.drop_table('edu_course')
