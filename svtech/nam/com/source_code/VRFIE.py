import MySQLdb
from jinja2 import Environment, FileSystemLoader
from Utils import Utils
import Database


class PSTERM:
    def __init__(self):
        self.term_name = ""
        self.acl = ""
        self.protocol = ""
        self.route_filter = ""
        self.action = ""

class VRFIE:
    db = Database.Database.db
    cursor = Database.Database.cursor

    def __init__(self, hostname, service_name, service_name_out):
        self.list_extcomm_exp_default = []
        self.list_extcomm_imp_default = []
        # self.acl = ""
        # self.extcomm = ""
        # self.term_name = "" # service_name + seq
        # list extcomm_term_name_seq contains tuple include 3 info term_name, acl, extcomm [(term_name, acl, extcomm)]
        self.list_extcomm_term_name_seq = []
        self.hostname = hostname
        self.service_name = service_name
        self.service_name_out = service_name_out

    @staticmethod
    def query_data(vrf_service_list):
        try:
            print ("coming into SQL")

            list_vrfie = []
            for vrf in vrf_service_list:
                hostname = vrf.hostname
                vrf_name = vrf.name
                vrf_name_out = vrf.name_out
                # print ("hostname: " + hostname + " vrfname :" + vrf_name)

                # select default export data from pair (hostname and vrf_name)

                list_rows_df_exp = vrf.exp_extcom.split()
                # select default import data from pair (hostname and vrf_name)
                list_rows_df_imp = vrf.imp_extcom.split()

                # select export map data from pair (hostname and vrf_name)
                sql_query_exp = "select Name, Seq, ACL, Protocol, Route_filter, Action from vrf_ie " \
                                "where Hostname = '%s' and VRF_Name = '%s' " \
                                % (hostname, vrf_name)
                VRFIE.cursor.execute(sql_query_exp)
                list_rows_exp = VRFIE.cursor.fetchall()

                data = VRFIE.extract_data(list_rows_df_exp, list_rows_df_imp, list_rows_exp, hostname, vrf_name, vrf_name_out)
                list_vrfie.append(data)
            return list_vrfie
        except MySQLdb.Error, e:
            print (e)
            # rollback in case there is any error
            VRFIE.db.rollback()

    @staticmethod
    def extract_data(list_rows_df_exp, list_rows_df_imp, list_rows_exp, hostname, vrf_name, vrf_name_out):

        vrfie = VRFIE(hostname, vrf_name, vrf_name_out)
        # cach viet functional programming

        vrfie.list_extcomm_exp_default = list_rows_df_exp
        vrfie.list_extcomm_imp_default = list_rows_df_imp
        if len(list_rows_exp) > 0:
            for row in list_rows_exp:
                psterm = PSTERM()
                psterm.term_name = row[0] + "_" + str(row[1])
                psterm.acl = row[2]
                psterm.protocol = row[3]
                psterm.route_filter = Utils.convert_subnet(row[4])
                psterm.action = row[5]
                vrfie.list_extcomm_term_name_seq.append(psterm)
        return vrfie

    @staticmethod
    def get_all_extcomm(vrfie_list):
        list_all_extcomm = []
        try:
            for vrfie in vrfie_list:
                list_all_extcomm += vrfie.list_extcomm_exp_default + vrfie.list_extcomm_imp_default
            # merge element with the same value
            list_all_extcomm = list(set(list_all_extcomm))
            return list_all_extcomm
        except MySQLdb.Error, e:
            print (e)
            VRFIE.db.rollback()

    @staticmethod
    def writefile(vrfie_list, list_all_extomm_from_VRFIE, file_name, path_input, path_output, hostname):
        template_env = Environment(autoescape=False, loader=FileSystemLoader(path_input), trim_blocks=False)
        policy_option = {'vrfie_list': vrfie_list, 'list_all_extcomm': list_all_extomm_from_VRFIE}
        file_ouput = path_output + "/" + hostname
        with open(file_ouput, 'a') as f:
            f_txt = template_env.get_template(file_name).render(policy_option)
            f.write(f_txt)
        print("write successful")

