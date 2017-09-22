import IFL
import netaddr as net
import string
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
        if (x != '') and ('-' not in x) and ('lo0' not in x):
            tmp = x.split()
            if len(tmp) == 1:
                if '/' in tmp[0]:
                    return tmp[0]
                else:
                    return tmp[0] + '/0'
            elif len(tmp) > 1:
                if tmp[1]=='0':
                    return tmp[0]+'/32'
                else:
                    ip = net.IPNetwork(tmp[0] + '/' + tmp[1])
                    host = str(ip.network)
                    subnet = str(ip.prefixlen)
                    return host + '/' + subnet
        elif '-' in x :
            tmp_x = string.replace(x, '-', ':', 2).split()[0]
            return tmp_x
        else:
            return x

    @staticmethod
    def convert_ip(x):
        ip = ''
        if 'lo0' not in x:
            host, subnet = x.strip().split()[0] , x.strip().split()[1]
            subnet_host = host + '/' + subnet
            # print("subnet_mask: " + subnet_mask)
            # print("network: " + str(network_ipv4))
            ip = str(net.IPNetwork(subnet_host))
            # check ',' and '-' in svlan and cvlan
        else:
            ip = x
        return ip

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
