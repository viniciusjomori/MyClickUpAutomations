import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import * as schedulerTargets from 'aws-cdk-lib/aws-scheduler-targets';

export interface DeleteOldEmptyTasksProps extends cdk.StackProps {
  envName: string,
  clickup: {
    apiKey: string,
    teamId: string
  },
  deleteOldEmptyTasks: {
    days: number,
    ignoredSpaceIds?: string[],
    schedules: DeleteOldEmptyTasksSchedule[]
  }
}

interface DeleteOldEmptyTasksSchedule {
  ruleId: string
  hour: string
  minute: string
  day?: string
  month?: string
  year?: string
  weekDay?: string
  timeZone?: string
}

export class DeleteOldEmptyTasksContruct extends Construct {
  constructor(scope: Construct, id: string, props: DeleteOldEmptyTasksProps) {
    super(scope, id);

    if (props.deleteOldEmptyTasks.schedules.length === 0) {
      return;
    }

    const fn = new lambda.DockerImageFunction(this, 'ClickUp-DeleteOldEmptyTasks', {
      functionName: `ClickUp-DeleteOldEmptyTasks-${props.envName}`,
      code: lambda.DockerImageCode.fromImageAsset('./images/deleteOldEmptyTasks'),
      memorySize: 1024,
      timeout: cdk.Duration.minutes(15),
      architecture: lambda.Architecture.X86_64,
      loggingFormat: lambda.LoggingFormat.JSON,
      environment: {
        CLICKUP_API_KEY: props.clickup.apiKey,
        CLICKUP_TEAM_ID: props.clickup.teamId,
        DELETE_OLD_EMPTY_TASKS_DAYS: props.deleteOldEmptyTasks.days.toString(),
        DELETE_OLD_EMPTY_TASKS_IGNORED_SPACE_IDS: (props.deleteOldEmptyTasks.ignoredSpaceIds ?? []).join(','),
        TZ: 'America/Sao_Paulo'
      }
    });

    for (const schedule of props.deleteOldEmptyTasks.schedules) {
      new scheduler.Schedule(this, `Schedule-Rule-DeleteOldEmptyTasks-${schedule.ruleId}`, {
        scheduleName: `ClickUp-DeleteOldEmptyTasks-${schedule.ruleId}-${props.envName}`,
        schedule: scheduler.ScheduleExpression.cron({
          hour: schedule.hour,
          minute: schedule.minute,
          day: schedule.day,
          month: schedule.month,
          year: schedule.year,
          weekDay: schedule.weekDay,
          timeZone: cdk.TimeZone.of(schedule.timeZone ?? 'America/Sao_Paulo'),
        }),
        target: new schedulerTargets.LambdaInvoke(fn),
        timeWindow: scheduler.TimeWindow.off(),
      });
    }
  }
}
