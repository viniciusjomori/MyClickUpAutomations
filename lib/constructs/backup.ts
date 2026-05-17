import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import * as schedulerTargets from 'aws-cdk-lib/aws-scheduler-targets';

export interface BackupProps extends cdk.StackProps {
  envName: string,
  clickup: {
    apiKey: string,
    teamId: string
  },
  backup: {
    schedules: BackupSchedule[]
  }
}

interface BackupSchedule {
  ruleId: string
  hour: string
  minute: string
  day?: string
  month?: string
  year?: string
  weekDay?: string
  timeZone?: string
}

export class BackupContruct extends Construct {
  constructor(scope: Construct, id: string, props: BackupProps) {
    super(scope, id);

    const envName = props.envName.toLowerCase()

    const bucket = new s3.Bucket(this, 'S3Bucket', {
        bucketName: `viniciusjomori-clickup-backup-${envName}`,
        versioned: false,
        removalPolicy: cdk.RemovalPolicy.DESTROY,
        autoDeleteObjects: true
    });

    const fn = new lambda.DockerImageFunction(this, "ClickUp-BackUp", {
        functionName: `ClickUp-BackUp-${props.envName}`,
        code: lambda.DockerImageCode.fromImageAsset("./images/backup"),
        memorySize: 1024,
        timeout: cdk.Duration.minutes(15),
        architecture: lambda.Architecture.X86_64,
        loggingFormat: lambda.LoggingFormat.JSON,
        environment: {
          CLICKUP_API_KEY: props.clickup.apiKey,
          CLICKUP_TEAM_ID: props.clickup.teamId,
          BUCKET_NAME: bucket.bucketName
        }
    });

    bucket.grantPut(fn)

    for (const schedule of props.backup.schedules) {
      new scheduler.Schedule(this, `Schedule-Rule-Backup-${schedule.ruleId}`, {
        scheduleName: `ClickUp-BackUp-${schedule.ruleId}-${props.envName}`,
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
