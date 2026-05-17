import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import * as schedulerTargets from 'aws-cdk-lib/aws-scheduler-targets';

export interface TagArchiveProps extends cdk.StackProps {
  envName: string,
  clickup: {
    apiKey: string,
    teamId: string
  },
  intertexto: {
    apiKey: string,
    state: string
  },
  tagArchive: TagArchiveRule[]
}

export type HolidayMode = 'ignore' | 'consider' | null;

interface ScheduleTime {
  hour: string
  minute: string
}

interface TagArchiveRule {
  ruleId: string
  tag: string
  archive: ScheduleTime
  unarchive: ScheduleTime
  weekDay: string
  holidays?: HolidayMode
  timeZone?: string
}

export class TagArchiveContruct extends Construct {
  constructor(scope: Construct, id: string, props: TagArchiveProps) {
    super(scope, id);

    if (props.tagArchive.length === 0) {
      return;
    }

    const fn = new lambda.DockerImageFunction(this, 'ClickUp-TagArchive', {
      functionName: `ClickUp-TagArchive-${props.envName}`,
      code: lambda.DockerImageCode.fromImageAsset('./images/tagArchive'),
      memorySize: 1024,
      timeout: cdk.Duration.minutes(15),
      architecture: lambda.Architecture.X86_64,
      loggingFormat: lambda.LoggingFormat.JSON,
      environment: {
        CLICKUP_API_KEY: props.clickup.apiKey,
        CLICKUP_TEAM_ID: props.clickup.teamId,
        INVERTEXTO_API_KEY: props.intertexto.apiKey ?? '',
        INVERTEXTO_STATE: props.intertexto.state ?? '',
        TZ: 'America/Sao_Paulo'
      }
    });

    for (const rule of props.tagArchive) {
      this.createSchedule(props, fn, rule, 'Archive', rule.archive, true);
      this.createSchedule(props, fn, rule, 'Unarchive', rule.unarchive, false);
    }
  }

  private createSchedule(
    props: TagArchiveProps,
    fn: lambda.IFunction,
    rule: TagArchiveRule,
    action: 'Archive' | 'Unarchive',
    scheduleTime: ScheduleTime,
    archived: boolean
  ) {
    new scheduler.Schedule(this, `Schedule-Rule-${rule.ruleId}-${action}`, {
      scheduleName: `ClickUp-TagArchive-${rule.ruleId}-${action}-${props.envName}`,
      schedule: scheduler.ScheduleExpression.cron({
        hour: scheduleTime.hour,
        minute: scheduleTime.minute,
        weekDay: rule.weekDay,
        timeZone: cdk.TimeZone.of(rule.timeZone ?? 'America/Sao_Paulo'),
      }),
      target: new schedulerTargets.LambdaInvoke(fn, {
        input: scheduler.ScheduleTargetInput.fromObject({
          tag: rule.tag,
          archived,
          holidays: rule.holidays ?? null,
        })
      }),
      timeWindow: scheduler.TimeWindow.off(),
    });
  }
}
