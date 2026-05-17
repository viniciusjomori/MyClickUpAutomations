import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import * as schedulerTargets from 'aws-cdk-lib/aws-scheduler-targets';

export interface RemindMeLaterProps extends cdk.StackProps {
  envName: string,
  clickup: {
    apiKey: string,
    teamId: string
  },
  remindMeLater: RemindMeLaterConfig
}

interface RemindMeLaterConfig {
  period: SchedulePeriod
  tags: RemindMeLaterTag[]
}

interface SchedulePeriod {
  hour: string
  minute: string
  weekDay?: string
  timeZone?: string
}

interface RemindMeLaterTag {
  tag: string
  delayMinutes: number
}

export class RemindMeLaterContruct extends Construct {
  constructor(scope: Construct, id: string, props: RemindMeLaterProps) {
    super(scope, id);

    if (props.remindMeLater.tags.length === 0) {
      return;
    }

    const period = props.remindMeLater.period;
    const fn = new lambda.DockerImageFunction(this, 'ClickUp-RemindMeLater', {
      functionName: `ClickUp-RemindMeLater-${props.envName}`,
      code: lambda.DockerImageCode.fromImageAsset('./images/remindMeLater'),
      memorySize: 1024,
      timeout: cdk.Duration.minutes(15),
      architecture: lambda.Architecture.X86_64,
      loggingFormat: lambda.LoggingFormat.JSON,
      environment: {
        CLICKUP_API_KEY: props.clickup.apiKey,
        CLICKUP_TEAM_ID: props.clickup.teamId,
        TZ: 'America/Sao_Paulo'
      }
    });

    new scheduler.Schedule(this, 'Schedule-Rule-RemindMeLater', {
      scheduleName: `ClickUp-RemindMeLater-${props.envName}`,
      schedule: scheduler.ScheduleExpression.cron({
        hour: period.hour,
        minute: period.minute,
        weekDay: period.weekDay ?? '*',
        timeZone: cdk.TimeZone.of(period.timeZone ?? 'America/Sao_Paulo'),
      }),
      target: new schedulerTargets.LambdaInvoke(fn, {
        input: scheduler.ScheduleTargetInput.fromObject({
          tags: props.remindMeLater.tags
        })
      }),
      timeWindow: scheduler.TimeWindow.off(),
    });
  }
}
