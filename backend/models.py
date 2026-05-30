import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Chapter(db.Model):
    __tablename__ = 'chapters'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship('Chapter', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    questions = db.relationship('Question', backref='chapter', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'order': self.order,
            'children': [c.to_dict() for c in self.children.order_by(Chapter.order).all()]
        }

class QuestionType(db.Model):
    __tablename__ = 'question_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    is_multiple = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship('Question', backref='question_type', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'is_multiple': self.is_multiple
        }

class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    stem = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=True)
    option_d = db.Column(db.Text, nullable=True)
    option_e = db.Column(db.Text, nullable=True)
    option_f = db.Column(db.Text, nullable=True)
    answer = db.Column(db.String(10), nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    stem_html = db.Column(db.Text, nullable=True)
    option_a_html = db.Column(db.Text, nullable=True)
    option_b_html = db.Column(db.Text, nullable=True)
    option_c_html = db.Column(db.Text, nullable=True)
    option_d_html = db.Column(db.Text, nullable=True)
    option_e_html = db.Column(db.Text, nullable=True)
    option_f_html = db.Column(db.Text, nullable=True)
    explanation_html = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='published')
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=True)
    question_type_id = db.Column(db.Integer, db.ForeignKey('question_types.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, shuffle_options=False):
        result = {
            'id': self.id,
            'stem': self.stem,
            'stem_html': self.stem_html,
            'option_a': self.option_a,
            'option_a_html': self.option_a_html,
            'option_b': self.option_b,
            'option_b_html': self.option_b_html,
            'option_c': self.option_c,
            'option_c_html': self.option_c_html,
            'option_d': self.option_d,
            'option_d_html': self.option_d_html,
            'option_e': self.option_e,
            'option_e_html': self.option_e_html,
            'option_f': self.option_f,
            'option_f_html': self.option_f_html,
            'answer': self.answer,
            'explanation': self.explanation,
            'explanation_html': self.explanation_html,
            'difficulty': self.difficulty,
            'status': self.status,
            'chapter_id': self.chapter_id,
            'question_type_id': self.question_type_id,
            'question_type_name': self.question_type.name if self.question_type else None,
            'chapter_name': self.chapter.name if self.chapter else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if shuffle_options:
            options = []
            option_labels = ['A', 'B', 'C', 'D', 'E', 'F']
            option_keys = ['option_a', 'option_b', 'option_c', 'option_d', 'option_e', 'option_f']
            option_html_keys = ['option_a_html', 'option_b_html', 'option_c_html', 'option_d_html', 'option_e_html', 'option_f_html']
            for i, key in enumerate(option_keys):
                if getattr(self, key):
                    options.append({
                        'label': option_labels[i],
                        'content': getattr(self, key),
                        'html': getattr(self, option_html_keys[i])
                    })
            import random
            random.shuffle(options)
            result['shuffled_options'] = options
            original_answer = self.answer.upper()
            answer_map = {}
            for idx, opt in enumerate(options):
                answer_map[opt['label']] = idx
            new_answer = ''.join([str(answer_map.get(c, c)) for c in original_answer])
            result['shuffled_answer'] = new_answer
        return result

class WrongQuestion(db.Model):
    __tablename__ = 'wrong_questions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False, default='default_user')
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    wrong_count = db.Column(db.Integer, default=1)
    reappearance_count = db.Column(db.Integer, default=0)
    first_wrong_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_wrong_at = db.Column(db.DateTime, default=datetime.utcnow)
    question = db.relationship('Question', backref='wrong_records')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'question_id': self.question_id,
            'wrong_count': self.wrong_count,
            'reappearance_count': self.reappearance_count,
            'first_wrong_at': self.first_wrong_at.isoformat() if self.first_wrong_at else None,
            'last_wrong_at': self.last_wrong_at.isoformat() if self.last_wrong_at else None,
            'question': self.question.to_dict() if self.question else None
        }

class FavoriteQuestion(db.Model):
    __tablename__ = 'favorite_questions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False, default='default_user')
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    question = db.relationship('Question', backref='favorite_records')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'question_id': self.question_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'question': self.question.to_dict() if self.question else None
        }

class UserAnswer(db.Model):
    __tablename__ = 'user_answers'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    user_answer = db.Column(db.String(10), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)
    question = db.relationship('Question', backref='user_answers')

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'question_id': self.question_id,
            'user_answer': self.user_answer,
            'is_correct': self.is_correct,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None
        }

class UserPreference(db.Model):
    __tablename__ = 'user_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False, default='default_user')
    eye_protection_mode = db.Column(db.String(20), default='none')
    font_size = db.Column(db.Integer, default=16)
    font_family = db.Column(db.String(50), default='Microsoft YaHei')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'eye_protection_mode': self.eye_protection_mode,
            'font_size': self.font_size,
            'font_family': self.font_family
        }

class OperationLog(db.Model):
    __tablename__ = 'operation_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False, default='system')
    action = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
