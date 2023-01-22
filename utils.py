from dataclasses import dataclass

def filter_tasks_by_status(tasks,status):
    return filter(lambda task: task.status ==status,tasks)

@dataclass(frozen=True)
class Status:
    TO_DO = "TO_DO"
    IN_PROGRESS = "INPROGRESS"
    DONE = "DONE"

constStatus = Status()