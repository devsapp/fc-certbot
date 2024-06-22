"use strict";

const CERT_PREFIX = "devs-certbot-generated-";
const CERT_WILDCARD_PREFIX = "devs-certbot-generated-w-";

const FC20230330 = require("@alicloud/fc20230330");
const cas20200407 = require("@alicloud/cas20200407");
const OpenApi = require("@alicloud/openapi-client");
const Util = require("@alicloud/tea-util");
const Stream = require("@alicloud/darabonba-stream");
const _ = require("lodash");
const runtime = new Util.RuntimeOptions({});
const CERT_GENERATOR_FUNCTION_NAME = process.env.CERT_GENERATOR_FUNCTION_NAME;

function getFcClient(regionId, context) {
  return new FC20230330.default(
    new OpenApi.Config({
      accessKeyId: context.credentials.accessKeyId,
      accessKeySecret: context.credentials.accessKeySecret,
      securityToken: context.credentials.securityToken,
      endpoint: `${context.accountId}.${regionId}${
        regionId === context.region ? "-internal" : ""
      }.fc.aliyuncs.com`,
      readTimeout: 1000000,
      connectTimeout: 1000000,
    })
  );
}

function getCasClient(context) {
  return new cas20200407.default(
    new OpenApi.Config({
      accessKeyId: context.credentials.accessKeyId,
      accessKeySecret: context.credentials.accessKeySecret,
      securityToken: context.credentials.securityToken,
      endpoint: "cas.aliyuncs.com",
      readTimeout: 1000000,
      connectTimeout: 1000000,
    })
  );
}

async function listCustomDomains(regionId, context) {
  const client = getFcClient(regionId, context);
  let nextToken = "";
  let stop = false;
  const out = [];
  while (!stop) {
    const result = await client.listCustomDomainsWithOptions(
      new FC20230330.ListCustomDomainsRequest({
        nextToken,
        limit: 100,
      }),
      {},
      runtime
    );
    out.push(
      ...result.body.customDomains.filter((customDomain) => {
        const { protocol, certConfig } = customDomain;
        if (
          protocol.toLocaleLowerCase().includes("https") &&
          certConfig.certName.startsWith(CERT_PREFIX)
        ) {
          customDomain.regionId = regionId;
          return true;
        } else {
          return false;
        }
      })
    );
    if (result.body.nextToken) {
      nextToken = result.body.nextToken;
    } else {
      stop = true;
    }
  }

  return out;
}

async function updateCustomDomain(customDomain, certName, certInfo, context) {
  await getFcClient(
    customDomain.regionId,
    context
  ).updateCustomDomainWithOptions(
    customDomain.domainName,
    new FC20230330.UpdateCustomDomainRequest({
      body: new FC20230330.UpdateCustomDomainInput({
        certConfig: new FC20230330.CertConfig({
          certName,
          certificate: certInfo.body.cert,
          privateKey: certInfo.body.key,
        }),
      }),
    }),
    {},
    runtime
  );
  console.log(`update ${customDomain.domainName} success`);
}
async function updateCustomDomains(certName, customDomains, context) {
  const fcClient = getFcClient(context.region, context);
  const casClient = getCasClient(context);
  const domainNames = _.uniq(
    customDomains.map((customDomain) => customDomain.domainName)
  );
  let domainName = domainNames[0];
  if (domainNames.length > 1) {
    if (certName.startsWith(CERT_WILDCARD_PREFIX)) {
      const wildcardPosition = Number(certName.split("-")[4]);
      domainName = `*.${domainName
        .split(".")
        .slice(-1 * (wildcardPosition - 1))
        .join(".")}`;
    }
  }
  const result = await fcClient.invokeFunctionWithOptions(
    CERT_GENERATOR_FUNCTION_NAME,
    new FC20230330.InvokeFunctionRequest({
      body: Stream.default.readFromString(
        JSON.stringify({
          certName,
          domainName,
        })
      ),
    }),
    new FC20230330.InvokeFunctionHeaders({
      xFcInvocationType: "Sync",
    }),
    new Util.RuntimeOptions({})
  );
  if (!result.headers["x-fc-error-type"]) {
    const certId = await Util.default.readAsString(result.body);
    if (certId) {
      const certInfo = await casClient.getUserCertificateDetailWithOptions(
        new cas20200407.GetUserCertificateDetailRequest({
          certId: certId,
        }),
        runtime
      );
      await Promise.all([
        ...customDomains
          .filter((customDomain) => {
            if (customDomain.certConfig.certificate !== certInfo.body.cert) {
              return true;
            } else {
              console.log(
                `No need to update ${customDomain.domainName} because it already has the latest cert`
              );
              return false;
            }
          })
          .map((customDomain) =>
            updateCustomDomain(customDomain, certName, certInfo, context)
          ),
      ]);
    } else {
      throw new Error(`Failed to find cert ${certName}`);
    }
  } else {
    throw new Error(`Failed to check cert ${certName}`);
  }
}

exports.handler = async (event, context, callback) => {
  let out = await Promise.all(
    process.env.CUSTOM_DOMAIN_REGIONS.split(",").map((regionId) =>
      listCustomDomains(regionId, context)
    )
  );
  out = out.flat();
  const map = {};
  out.forEach((c) => {
    const certName = c.certConfig.certName;
    if (map[certName]) {
      map[certName].push(c);
    } else {
      map[certName] = [c];
    }
  });

  const requests = [];
  if (Object.keys(map).length === 0) {
    console.log("no fc-certbot app created certs found");
  }
  Object.keys(map).forEach(async (certName) => {
    const customDomains = map[certName];
    console.log(
      `found cert ${certName} is used by custom domains: ${customDomains
        .map((c) => c.domainName)
        .join(", ")}.`
    );
    requests.push(updateCustomDomains(certName, customDomains, context));
  });
  await Promise.all(requests);
  callback(null, "done");
};
