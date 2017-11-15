from apscheduler.schedulers.blocking import BlockingScheduler
import check

sched = BlockingScheduler()


@sched.scheduled_job('cron', day_of_week='mon-fri', hour=15)
def scheduled_job():
    check.main()

sched.start()
