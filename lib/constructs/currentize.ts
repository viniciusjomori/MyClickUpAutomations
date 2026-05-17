import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import * as schedulerTargets from 'aws-cdk-lib/aws-scheduler-targets';

export interface CurrentizeProps extends cdk.StackProps {
  envName: string,
  clickup: {
    apiKey: string,
    teamId: string
  },
  currentize: {
    schedules: CurrentizeSchedule[]
  }
}

interface CurrentizeSchedule {
  ruleId: string
  hour: string
  minute: string
  day?: string
  month?: string
  year?: string
  weekDay?: string
  timeZone?: string
}

export class CurrentizeContruct extends Construct {
  constructor(scope: Construct, id: string, props: CurrentizeProps) {
    super(scope, id);

    const fn = new lambda.DockerImageFunction(this, "ClickUp-Currentize", {
        functionName: `ClickUp-Currentize-${props.envName}`,
        code: lambda.DockerImageCode.fromImageAsset("./images/currentize"),
        memorySize: 1024,
        timeout: cdk.Duration.minutes(15),
        architecture: lambda.Architecture.X86_64,
        loggingFormat: lambda.LoggingFormat.JSON,
        environment: {
            CLICKUP_API_KEY: props.clickup.apiKey,
            CLICKUP_TEAM_ID: props.clickup.teamId,
            TZ: "America/Sao_Paulo"
        }
    });

    for (const schedule of props.currentize.schedules) {
      new scheduler.Schedule(this, `Schedule-Rule-Currentize-${schedule.ruleId}`, {
        scheduleName: `ClickUp-Currentize-${schedule.ruleId}-${props.envName}`,
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
      })
    }
    
  }
}
