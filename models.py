from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class Project(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    owner_id=db.Column(db.String(100))
    name = db.Column(db.String(200))
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())

    tasks = relationship(
        'Task',
        back_populates='project',
        cascade='save-update, merge, delete'
    )
    
class Task(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    project_id = db.Column(db.Integer,db.ForeignKey(Project.id))
    name = db.Column(db.String(200))
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    status = db.Column(db.String(30))

    project = relationship(
        'Project',
        back_populates='tasks',
    )
