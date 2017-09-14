import MySQLdb
from jinja2 import Environment, FileSystemLoader
import Database

class PSTERM:
    def __init__(self):
        self.term_name = ""
        self.acl = ""
        self.extcomm = ""

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
            name_default = '%default%'
            list_vrfie = []
            for vrf in vrf_service_list:
                hostname = vrf.hostname
                vrf_name = vrf.name
                vrf_name_out = vrf.name_out
                # print ("hostname: " + hostname + " vrfname :" + vrf_name)
                # select default export data from pair (hostname and vrf_name)
                sql_query_df_exp = "select Extcomm from vrf_ie where Hostname = '%s' and VRF_Name = '%s' and Name like '%s' and IE = '%s'" \
                            % (hostname, vrf_name, name_default, 'exp')
                VRFIE.cursor.execute(sql_query_df_exp)
                list_rows_df_exp = VRFIE.cursor.fetchall()

                # select default import data from pair (hostname and vrf_name)

                sql_query_df_imp = "select Extcomm from vrf_ie where Hostname = '%s' and VRF_Name = '%s' and Name like '%s' and IE = '%s'" \
                            % (hostname, vrf_name, name_default, 'imp')
                VRFIE.cursor.execute(sql_query_df_imp)
                list_rows_df_imp = VRFIE.cursor.fetchall()

                # select export map data from pair (hostname and vrf_name)

                sql_query_exp = "select Name, Seq, ACL, Extcomm from vrf_ie where Hostname = '%s' and VRF_Name = '%s' and Name not like '%s'" \
                            % (hostname, vrf_name, name_default)
                VRFIE.cursor.execute(sql_query_exp)
                list_rows_exp = VRFIE.cursor.fetchall()

                data = VRFIE.extract_data(list_rows_df_exp,list_rows_df_imp,list_rows_exp, hostname, vrf_name, vrf_name_out)
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
        vrfie.list_extcomm_exp_default = list(map(lambda x: x[0], list_rows_df_exp))
        vrfie.list_extcomm_imp_default = list(map(lambda x: x[0], list_rows_df_imp))

        if len(list_rows_exp) > 0:
            for row in list_rows_exp:
                psterm = PSTERM()
                psterm.term_name = row[0] + "_" + str(row[1])
                psterm.acl = row[2]
                psterm.extcomm = row[3]
                vrfie.list_extcomm_term_name_seq.append(psterm)
        return vrfie

    @staticmethod
    def get_all_extcomm(hostname):
        try:
            # select all extcomm
            sql_query_all_extcomm = "select Extcomm from vrf_ie where Hostname = '%s'" % hostname
            VRFIE.cursor.execute(sql_query_all_extcomm)
            list_rows_all_extcomm = VRFIE.cursor.fetchall()
            list_temp = list(map(lambda x: x[0], list_rows_all_extcomm))
            list_all_extcomm = list(filter(lambda x: len(x) > 0, list_temp))
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

