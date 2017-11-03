from apscheduler.schedulers.blocking import BlockingScheduler
from check import main
sched = BlockingScheduler()


@sched.scheduled_job('cron', day_of_week='mon-fri', hour=12)
def scheduled_job():
    main()
    print('This job is run every weekday at 12pm.')

sched.start()
