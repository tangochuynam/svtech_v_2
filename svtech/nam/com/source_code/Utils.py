import IFL
import netaddr as net
class Utils:
    def __init__(self):
        pass

    @staticmethod
    def convert(x):
        interface_unit = IFL.INTERFACE_UNIT(x[0], x[1], "", "")
        interface_unit.ip_helper_list = x[2].split(' ')
        return interface_unit

    @staticmethod
    def convert_subnet(x):
        if x != '':
            tmp = x.split()
            if len(tmp) == 1:
                return tmp[0] + '/0'
            elif len(tmp) > 1:
                ip = net.IPNetwork(tmp[0] + '/' + tmp[1])
                host = str(ip.network)
                subnet = str(ip.prefixlen)
                return host + '/' + subnet
        else:
            return x
    @staticmethod
    def change_name_classifier(classifier):
        #print ("gia tri classifier: " + classifier)
        if classifier.startswith('af3'):
            name_out = 'L1'
        elif classifier.startswith('af2'):
            name_out = 'AF'
        elif classifier.startswith('af4'):
            name_out = 'H2'
        elif classifier.startswith('ef'):
            name_out = 'EF'
        elif classifier.startswith(('default', 'be')):
            name_out = 'BE'
        else:
            name_out = classifier.strip()
        return name_out
