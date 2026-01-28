from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Analysis(db.Model):
    """Model for storing analysis results"""
    __tablename__ = 'analyses'
    
    id = db.Column(db.String(64), primary_key=True)
    candidate_name = db.Column(db.String(200))
    filename = db.Column(db.String(500))
    job_description_hash = db.Column(db.String(64))
    overall_score = db.Column(db.Integer)
    grade = db.Column(db.String(10))
    recommendation = db.Column(db.String(500))
    analysis_data = db.Column(db.Text)  # JSON data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_created_at', 'created_at'),
        db.Index('idx_score', 'overall_score'),
        db.Index('idx_filename', 'filename'),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'candidate_name': self.candidate_name,
            'filename': self.filename,
            'overall_score': self.overall_score,
            'grade': self.grade,
            'recommendation': self.recommendation,
            'analysis_data': json.loads(self.analysis_data) if self.analysis_data else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class BatchAnalysis(db.Model):
    """Model for storing batch analysis results"""
    __tablename__ = 'batch_analyses'
    
    id = db.Column(db.String(64), primary_key=True)
    batch_id = db.Column(db.String(64), unique=True)
    total_files = db.Column(db.Integer)
    successfully_analyzed = db.Column(db.Integer)
    failed_files = db.Column(db.Integer)
    analysis_data = db.Column(db.Text)  # JSON data
    excel_report_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_batch_id', 'batch_id'),
        db.Index('idx_batch_created', 'created_at'),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'total_files': self.total_files,
            'successfully_analyzed': self.successfully_analyzed,
            'failed_files': self.failed_files,
            'analysis_data': json.loads(self.analysis_data) if self.analysis_data else {},
            'excel_report_path': self.excel_report_path,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SkillTrend(db.Model):
    """Model for tracking skill trends"""
    __tablename__ = 'skill_trends'
    
    id = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(200))
    frequency = db.Column(db.Integer, default=0)
    industry = db.Column(db.String(100))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_skill_name', 'skill_name'),
        db.Index('idx_industry', 'industry'),
        db.Index('idx_frequency', 'frequency'),
    )

class Cache(db.Model):
    """Model for caching analysis results"""
    __tablename__ = 'cache'
    
    key = db.Column(db.String(512), primary_key=True)
    value = db.Column(db.Text)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_expires', 'expires_at'),
    )
