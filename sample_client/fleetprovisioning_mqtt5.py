# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from awscrt import mqtt5, http
from awsiot import iotidentity, mqtt5_client_builder
from concurrent.futures import Future
import sys
import threading
import time
import traceback
import json

import re
# from utils.command_line_utils import CommandLineUtils # We need to make it a non CMD line thing

# - Overview -
# This sample uses the AWS IoT Fleet Provisioning to provision device using either the keys
# or CSR
#
#
# - Instructions -
# This sample requires you to create a provisioning claim. See:
# https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html
#
# - Detail -
# On startup, the script subscribes to topics based on the request type of either CSR or Keys
# publishes the request to corresponding topic and calls RegisterThing.

# cmdData is the arguments/input from the command line placed into a single struct for
# use in this sample. This handles all of the command line parsing, validating, etc.
# See the Utils/CommandLineUtils for more information.
# cmdData = CommandLineUtils.parse_sample_input_fleet_provisioning()

# Using globals to simplify sample code
is_sample_done = threading.Event()
mqtt5_client = None
identity_client = None
createKeysAndCertificateResponse = None
createCertificateFromCsrResponse = None
registerThingResponse = None
future_connection_success = Future()
args = None


class LockedData:
    def __init__(self):
        self.lock = threading.Lock()
        self.disconnect_called = False


locked_data = LockedData()


# Function for gracefully quitting this sample
def exit(msg_or_exception):
    if isinstance(msg_or_exception, Exception):
        print("Exiting Sample due to exception.")
        traceback.print_exception(
            msg_or_exception.__class__, msg_or_exception, sys.exc_info()[2])
    else:
        print("Exiting Sample:", msg_or_exception)

    global mqtt5_client
    with locked_data.lock:
        if not locked_data.disconnect_called:
            print("Stop the Client...")
            locked_data.disconnect_called = True
            if mqtt5_client:
                mqtt5_client.stop()
            else:
                print("No Client to stop")
                is_sample_done.set()


# Callback for the lifecycle event Connection Success
def on_lifecycle_connection_success(lifecycle_connect_success_data: mqtt5.LifecycleConnectSuccessData):
    print("Lifecycle Connection Success")
    global future_connection_success
    future_connection_success.set_result(lifecycle_connect_success_data)


# Callback for the lifecycle event on Client Stopped
def on_lifecycle_stopped(lifecycle_stopped_data: mqtt5.LifecycleStoppedData):
    # type: (Future) -> None
    print("Client Stopped.")
    # Signal that sample is finished
    is_sample_done.set()


def on_publish_register_thing(future):
    # type: (Future) -> None
    try:
        future.result()  # raises exception if publish failed
        print("Published RegisterThing request..")

    except Exception as e:
        print("Failed to publish RegisterThing request.")
        exit(e)


def on_publish_create_keys_and_certificate(future):
    # type: (Future) -> None
    try:
        future.result()  # raises exception if publish failed
        print("Published CreateKeysAndCertificate request..")

    except Exception as e:
        print("Failed to publish CreateKeysAndCertificate request.")
        exit(e)


def on_publish_create_certificate_from_csr(future):
    # type: (Future) -> None
    try:
        future.result()  # raises exception if publish failed
        print("Published CreateCertificateFromCsr request..")

    except Exception as e:
        print("Failed to publish CreateCertificateFromCsr request.")
        exit(e)


def createkeysandcertificate_execution_accepted(response):
    # type: (iotidentity.CreateKeysAndCertificateResponse) -> None
    try:
        global createKeysAndCertificateResponse
        createKeysAndCertificateResponse = response
        if (args.is_ci == False):
            print("Received a new message {}".format(
                createKeysAndCertificateResponse))

        return

    except Exception as e:
        exit(e)


def createkeysandcertificate_execution_rejected(rejected):
    # type: (iotidentity.RejectedError) -> None
    exit("CreateKeysAndCertificate Request rejected with code:'{}' message:'{}' status code:'{}'".format(
        rejected.error_code, rejected.error_message, rejected.status_code))


def createcertificatefromcsr_execution_accepted(response):
    # type: (iotidentity.CreateCertificateFromCsrResponse) -> None
    try:
        global createCertificateFromCsrResponse
        createCertificateFromCsrResponse = response
        if (args.is_ci == False):
            print("Received a new message {}".format(
                createCertificateFromCsrResponse))
        global certificateOwnershipToken
        certificateOwnershipToken = response.certificate_ownership_token

        return

    except Exception as e:
        exit(e)


def createcertificatefromcsr_execution_rejected(rejected):
    # type: (iotidentity.RejectedError) -> None
    exit("CreateCertificateFromCsr Request rejected with code:'{}' message:'{}' status code:'{}'".format(
        rejected.error_code, rejected.error_message, rejected.status_code))


def registerthing_execution_accepted(response):
    # type: (iotidentity.RegisterThingResponse) -> None
    try:
        global registerThingResponse
        registerThingResponse = response
        if (args.is_ci == False):
            print("Received a new message {} ".format(registerThingResponse))
        writeDeviceCertificateToDisk()
        return

    except Exception as e:
        exit(e)


def registerthing_execution_rejected(rejected):
    # type: (iotidentity.RejectedError) -> None
    global registerThingResponse
    registerThingResponse = rejected
    exit("RegisterThing Request rejected with code:'{}' message:'{}' status code:'{}'".format(
        rejected.error_code, rejected.error_message, rejected.status_code))


def on_resubscribe_complete(resubscribe_future):
    resubscribe_results = resubscribe_future.result()
    print("Resubscribe results: {}".format(resubscribe_results))

    for topic, qos in resubscribe_results['topics']:
        if qos is None:
            sys.exit("Server rejected resubscribe to topic: {}".format(topic))


def waitForCreateKeysAndCertificateResponse():
    # Wait for the response.
    loopCount = 0
    while loopCount < 10 and createKeysAndCertificateResponse is None:
        if createKeysAndCertificateResponse is not None:
            break
        if not args.is_ci:
            print('Waiting... CreateKeysAndCertificateResponse: ' +
                  json.dumps(createKeysAndCertificateResponse))
        else:
            print("Waiting... CreateKeysAndCertificateResponse: ...")
        loopCount += 1
        time.sleep(1)


def waitForCreateCertificateFromCsrResponse():
    # Wait for the response.
    loopCount = 0
    while loopCount < 10 and createCertificateFromCsrResponse is None:
        if createCertificateFromCsrResponse is not None:
            break
        if not args.is_ci:
            print('Waiting...CreateCertificateFromCsrResponse: ' +
                  json.dumps(createCertificateFromCsrResponse))
        else:
            print("Waiting... CreateCertificateFromCsrResponse: ...")
        loopCount += 1
        time.sleep(1)


def waitForRegisterThingResponse():
    # Wait for the response.
    loopCount = 0
    while loopCount < 20 and registerThingResponse is None:
        if registerThingResponse is not None:
            break
        loopCount += 1
        if not args.is_ci:
            print('Waiting... RegisterThingResponse: ' +
                  json.dumps(registerThingResponse))
        else:
            print('Waiting... RegisterThingResponse: ...')
        time.sleep(1)


def writeDeviceCertificateToDisk():
    try:
        # write cert to file
        r = re.search(
            r"(-----BEGIN CERTIFICATE-----).*?(-----END CERTIFICATE-----)",
            str(createKeysAndCertificateResponse),
            flags=re.DOTALL,
        ).group(0)
        with open(args.out_cert_file, "a") as f:
            f.write(r.replace("\\n", "\n").replace("\\t", "\t"))
        # write key to file
        r = re.search(
            r"(-----BEGIN RSA PRIVATE KEY-----).*?(-----END RSA PRIVATE KEY-----)",
            str(createKeysAndCertificateResponse),
            flags=re.DOTALL,
        ).group(0)
        with open(args.out_key_file, "a") as f:
            f.write(r.replace("\\n", "\n").replace("\\t", "\t"))
    except Exception as e:
        exit(e)


def main(argstoset):
    global args
    args = argstoset
    # Create the proxy options if the data is present in args
    proxy_options = None
    if args.proxy_host is not None and args.proxy_port != 0:
        proxy_options = http.HttpProxyOptions(
            host_name=args.proxy_host,
            port=args.proxy_port
        )

    # Create a MQTT connection from the input data
    mqtt5_client = mqtt5_client_builder.mtls_from_path(
        endpoint=args.endpoint,
        cert_filepath=args.enrollment_cert_file,
        pri_key_filepath=args.enrollment_key_file,
        ca_filepath=args.root_ca,
        client_id=args.client_id,
        clean_session=False,
        keep_alive_secs=30,
        http_proxy_options=proxy_options,
        on_lifecycle_connection_success=on_lifecycle_connection_success,
        on_lifecycle_stopped=on_lifecycle_stopped
    )

    if not args.is_ci:
        print(f"Connecting to {args.endpoint} with client ID '{
              args.client_id}'...")
    else:
        print("Connecting to endpoint with client ID")

    mqtt5_client.start()

    identity_client = iotidentity.IotIdentityClient(mqtt5_client)

    # Wait for connection to be fully established.
    # Note that it's not necessary to wait, commands issued to the
    # mqtt5_client before its fully connected will simply be queued.
    # But this sample waits here so it's obvious when a connection
    # fails or succeeds.
    future_connection_success.result()
    print("Connected!")

    try:
        # Subscribe to necessary topics.
        # Note that is **is** important to wait for "accepted/rejected" subscriptions
        # to succeed before publishing the corresponding "request".

        # Keys workflow if csr is not provided
        if args.csr_path is None:
            createkeysandcertificate_subscription_request = iotidentity.CreateKeysAndCertificateSubscriptionRequest()

            print("Subscribing to CreateKeysAndCertificate Accepted topic...")
            createkeysandcertificate_subscribed_accepted_future, _ = identity_client.subscribe_to_create_keys_and_certificate_accepted(
                request=createkeysandcertificate_subscription_request,
                qos=mqtt5.QoS.AT_LEAST_ONCE,
                callback=createkeysandcertificate_execution_accepted)

            # Wait for subscription to succeed
            createkeysandcertificate_subscribed_accepted_future.result()

            print("Subscribing to CreateKeysAndCertificate Rejected topic...")
            createkeysandcertificate_subscribed_rejected_future, _ = identity_client.subscribe_to_create_keys_and_certificate_rejected(
                request=createkeysandcertificate_subscription_request,
                qos=mqtt5.QoS.AT_LEAST_ONCE,
                callback=createkeysandcertificate_execution_rejected)

            # Wait for subscription to succeed
            createkeysandcertificate_subscribed_rejected_future.result()
        else:
            createcertificatefromcsr_subscription_request = iotidentity.CreateCertificateFromCsrSubscriptionRequest()

            print("Subscribing to CreateCertificateFromCsr Accepted topic...")
            createcertificatefromcsr_subscribed_accepted_future, _ = identity_client.subscribe_to_create_certificate_from_csr_accepted(
                request=createcertificatefromcsr_subscription_request,
                qos=mqtt5.QoS.AT_LEAST_ONCE,
                callback=createcertificatefromcsr_execution_accepted)

            # Wait for subscription to succeed
            createcertificatefromcsr_subscribed_accepted_future.result()

            print("Subscribing to CreateCertificateFromCsr Rejected topic...")
            createcertificatefromcsr_subscribed_rejected_future, _ = identity_client.subscribe_to_create_certificate_from_csr_rejected(
                request=createcertificatefromcsr_subscription_request,
                qos=mqtt5.QoS.AT_LEAST_ONCE,
                callback=createcertificatefromcsr_execution_rejected)

            # Wait for subscription to succeed
            createcertificatefromcsr_subscribed_rejected_future.result()

        registerthing_subscription_request = iotidentity.RegisterThingSubscriptionRequest(
            template_name=args.fleet_template_name)

        print("Subscribing to RegisterThing Accepted topic...")
        registerthing_subscribed_accepted_future, _ = identity_client.subscribe_to_register_thing_accepted(
            request=registerthing_subscription_request,
            qos=mqtt5.QoS.AT_LEAST_ONCE,
            callback=registerthing_execution_accepted)

        # Wait for subscription to succeed
        registerthing_subscribed_accepted_future.result()

        print("Subscribing to RegisterThing Rejected topic...")
        registerthing_subscribed_rejected_future, _ = identity_client.subscribe_to_register_thing_rejected(
            request=registerthing_subscription_request,
            qos=mqtt5.QoS.AT_LEAST_ONCE,
            callback=registerthing_execution_rejected)
        # Wait for subscription to succeed
        registerthing_subscribed_rejected_future.result()

        fleet_template_name = args.fleet_template_name
        fleet_template_parameters = args.fleet_template_parameters
        if args.csr_path is None:
            print("Publishing to CreateKeysAndCertificate...")
            publish_future = identity_client.publish_create_keys_and_certificate(
                request=iotidentity.CreateKeysAndCertificateRequest(), qos=mqtt5.QoS.AT_LEAST_ONCE)
            publish_future.add_done_callback(
                on_publish_create_keys_and_certificate)

            waitForCreateKeysAndCertificateResponse()

            if createKeysAndCertificateResponse is None:
                raise Exception('CreateKeysAndCertificate API did not succeed')

            registerThingRequest = iotidentity.RegisterThingRequest(
                template_name=fleet_template_name,
                certificate_ownership_token=createKeysAndCertificateResponse.certificate_ownership_token,
                parameters=json.loads(fleet_template_parameters))
        else:
            print("Publishing to CreateCertificateFromCsr...")
            csrPath = open(args.csr_path, 'r').read()
            publish_future = identity_client.publish_create_certificate_from_csr(
                request=iotidentity.CreateCertificateFromCsrRequest(
                    certificate_signing_request=csrPath),
                qos=mqtt5.QoS.AT_LEAST_ONCE)
            publish_future.add_done_callback(
                on_publish_create_certificate_from_csr)

            waitForCreateCertificateFromCsrResponse()

            if createCertificateFromCsrResponse is None:
                raise Exception('CreateCertificateFromCsr API did not succeed')

            registerThingRequest = iotidentity.RegisterThingRequest(
                template_name=fleet_template_name,
                certificate_ownership_token=createCertificateFromCsrResponse.certificate_ownership_token,
                parameters=json.loads(fleet_template_parameters))

        print("Publishing to RegisterThing topic...")
        registerthing_publish_future = identity_client.publish_register_thing(
            registerThingRequest, mqtt5.QoS.AT_LEAST_ONCE)
        registerthing_publish_future.add_done_callback(
            on_publish_register_thing)

        waitForRegisterThingResponse()
        exit("success")

    except Exception as e:
        exit(e)

    # Wait for the sample to finish
    is_sample_done.wait()
    print(f"Thing name: {registerThingResponse.thing_name}")
