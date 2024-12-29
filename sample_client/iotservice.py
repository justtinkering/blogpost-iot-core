import configparser
import fleetprovisioning_mqtt5 as fleetprovisioning
import os

# Get the directory of the current script
script_directory = os.path.dirname(os.path.realpath(__file__))

config = configparser.ConfigParser()
config.read('config.ini')


class IotProvisioning:
    def __init__(
        self,
        out_cert_file,
        out_key_file,
        proxy_host,
        proxy_port,
        use_websocket,
        endpoint,
        signing_region,
        root_ca,
        client_id,
        enrollment_cert_file,
        enrollment_key_file,
        csr,
        fleet_template_name,
        fleet_template_parameters,
        is_ci=False,
        csr_path=None
    ):
        self.out_cert_file = out_cert_file
        self.out_key_file = out_key_file
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.use_websocket = use_websocket
        self.endpoint = endpoint
        self.signing_region = signing_region
        self.root_ca = root_ca
        self.client_id = client_id
        self.enrollment_cert_file = enrollment_cert_file
        self.enrollment_key_file = enrollment_key_file
        self.csr = csr
        self.fleet_template_name = fleet_template_name
        self.fleet_template_parameters = fleet_template_parameters
        self.is_ci = False
        self.csr_path = None


license = '123'

args = IotProvisioning(
    out_cert_file=f"{script_directory}/{config['DEFAULT']['out_cert_file']}",
    out_key_file=f"{script_directory}/{config['DEFAULT']['out_key_file']}",
    proxy_host=None,
    proxy_port=None,
    use_websocket=None,
    endpoint=config['DEFAULT']['endpoint'],
    signing_region='eu-west-1',
    root_ca=f"{script_directory}/{config['DEFAULT']['root_ca']}",
    client_id='iot-123',
    enrollment_cert_file=f"{
        script_directory}/{config['DEFAULT']['enrollment_cert_file']}",
    enrollment_key_file=f"{
        script_directory}/{config['DEFAULT']['enrollment_key_file']}",
    csr=None,
    fleet_template_name=config['DEFAULT']['fleet_template_name'],
    fleet_template_parameters=f"{{\"License\": \"{license}\"}}",
)

fleetprovisioning.main(args)
