#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { ClickUpAutomationStack } from '../lib/clickup-automation-stack';
import * as fs from 'fs'
import * as path from 'path'

const app = new cdk.App();

const envName = app.node.tryGetContext("env")
const props = getProps(envName)

new ClickUpAutomationStack(app, `ClickUpAutomationStack-${props.envName}`, props);

function getProps(envName: string) {
    const propsPath = path.resolve(__dirname, `../props/${envName}.json`)

    if (!fs.existsSync(propsPath))
        throw new Error(`Env not found: ${envName}`)

    const props = JSON.parse(fs.readFileSync(propsPath, 'utf-8'))

    return {
        envName: envName.toUpperCase(),
        ...props
    }
}
