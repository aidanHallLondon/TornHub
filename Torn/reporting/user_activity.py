import json
import os

# from Torn.charts import plt_save_image
from Torn.reporting.build_menus import _menu_item_for_file
from Torn.tables import html_table
# from string import Template
# import matplotlib.pyplot as plt
# import pandas as pd
# import numpy as np

 


def user_activity_json(conn,cursor,
                        path ="reports/user",
                        title_str="user_activity_json",
                        out_filename="activity_e",
                        exclude_chain=False):
    if not os.path.exists(path):
        os.makedirs(path)
    cursor.execute('''
       SELECT  
            avg(actions) as actions,
            avg(actions)-avg(chain_attacks) AS non_chain_actions,
            avg(attacks)-avg(chain_attacks) AS ad_hoc_attacks,  
            avg(chain_attacks) as chain_attacks,
            avg(revives) as revives,
            avg(users) as users_online,
            day_of_week, day_of_week_name,hour_of_day
        From users_activity
        WHERE month>date('now', '-90 days')
        GROUP BY day_of_week,day_of_week_name,hour_of_day 
        ORDER BY hour_of_day;
    ''')
    raw_data=cursor.fetchall()
    data={
        "meta_data":{
                "name":"user_activity",
                "source":"user_activity_json",
                "headings":["Actions per hour","Actions per hour (ex chain)", "Ad hoc Attacks",  "Chain Attacks", "Revives", "Active Users", "hour_of_day", "day_of_week_id","day_of_week_name"],           
            },
          "data":raw_data
    }
    # 
    with open(os.path.join(path, out_filename+'.json'), "w") as f:
        f.write(json.dumps(data,indent=4))
    print(f"{title_str} saved in {out_filename}")  

# def plt_line_chart_for_user_90_day_activity( data, data_col=0, data_label="actions"):
#     """Generates a line chart of user activity using Matplotlib."""
#     # Prepare data for plotting
#     days =  [s[1:] for s in sorted(list(set(str(row[5]) + row[6] for row in data)))]  # Get unique day names
#     days.append("Mean")
#     hours = sorted(list(set([int(row[4]) for row in data])))  # Get unique hours

#     # Create a dictionary to store actions for each day and hour
#     activity_data = {}
#     for day in days:
#         activity_data[day] = [0] * len(hours)  # Initialize with zeros for each hour

#     # Populate the activity data from the query results
#     for row in data:
#         actions = row[data_col]
#         day = row[6]
#         hour = int(row[4])
#         # Find the index of the hour in the sorted hours list
#         hour_index = hours.index(hour)
#         activity_data[day][hour_index] = actions
#         activity_data['Mean'][hour_index] =activity_data['Mean'][hour_index]+ actions/7

#     # Create the plot
#     plt.figure(figsize=(10, 6))  # Adjust figure size as needed
#     for day in days:
#         plt.plot(hours, activity_data[day], label=day,lw=6 if day=='Mean' else 2)

#     plt.xlabel("Hour of Day")
#     plt.ylabel(f"Total {data_label}")
#     plt.title(f"User {data_label} by Hour and Day")
#     plt.xticks(hours)  # Ensure all hours are displayed on the x-axis
#     plt.legend()
#     plt.grid(True)

# def user_activity(conn,cursor,
#                         template_file_path="templates/reports/user/activity.html",
#                         title_str="User activity over 90 days",
#                         table_title="User activity over 90 days",
#                         path ="reports/user",
#                         out_filename="activity",
#                         f_menu=[]):
#     content_html_str=""
#     chart_html_str=""
#     table_html_str=""
#     # 
#     user_activity_json(conn,cursor,path=path,out_filename="activity_e")
#     # 
#     # if not os.path.exists(path):
#     #     os.makedirs(path)
#     # # 
#     # cursor.execute('''
#     #    SELECT  
#     #         sum(actions),sum(attacks),sum(revives),sum(users),
#     #         hour_of_day, day_of_week, day_of_week_name
#     #     From users_activity
#     #     WHERE month>date('now', '-90 days')
#     #     GROUP BY hour_of_day, day_of_week, day_of_week_name
#     #     ORDER BY day_of_week,hour_of_day;
#     # ''')
#     # data=cursor.fetchall()
#     # # 
#     # data_col_label = "(unique) active" # USERS
#     # plt_line_chart_for_user_90_day_activity( data,3,data_col_label)
#     # out_filename_plot = out_filename+'_'+data_col_label
#     # plt_save_image(path, out_filename_plot, show_image=False, clear_image=True)
#     # chart_html_str+= f"""<div class="chart" id="chart-svg-{data_col_label}">
#     #                 <div class="svg-container">
#     #                 <img src="/user/{out_filename_plot+'.svg'}" alt="{data_col_label} chart" width="200" height="150">
#     #                 </div></div>"""
    
#     # data_col_label = "attacks or revives"
#     # plt_line_chart_for_user_90_day_activity( data,0,data_col_label)
#     # out_filename_plot = out_filename+'_'+data_col_label
#     # plt_save_image(path, out_filename_plot, show_image=False, clear_image=True)
#     # chart_html_str+= f"""<div class="chart" id="chart-svg-{data_col_label}">
#     #                 <div class="svg-container">
#     #                 <img src="/user/{out_filename_plot+'.svg'}" alt="{data_col_label} chart" width="200" height="150">
#     #                 </div></div>"""
 
#     # data_col_label = "attacks"
#     # plt_line_chart_for_user_90_day_activity( data,1,data_col_label)
#     # out_filename_plot = out_filename+'_'+data_col_label
#     # plt_save_image(path, out_filename_plot, show_image=False, clear_image=True)
#     # chart_html_str+= f"""<div class="chart" id="chart-svg-{data_col_label}">
#     # <div class="svg-container">
#     # <img src="/user/{out_filename_plot+'.svg'}" alt="{data_col_label} chart" width="200" height="150">
#     # </div></div>"""
 

#     # data_col_label = "revives"
#     # plt_line_chart_for_user_90_day_activity( data,2,data_col_label)
#     # out_filename_plot = out_filename+'_'+data_col_label
#     # plt_save_image(path, out_filename_plot, show_image=False, clear_image=True)
#     # chart_html_str+= f"""<div class="chart" id="chart-svg-{data_col_label}">
#     # <div class="svg-container">
#     # <img src="/user/{out_filename_plot+'.svg'}" alt="{data_col_label} chart" width="200" height="150">
#     # </div></div>"""
#     # # 
#     # content_html_str=chart_html_str
#     # print(content_html_str)
#     # # 
#     # with open(template_file_path, "r") as f:
#     #     html_template = Template(f.read())
#     # final_html = html_template.safe_substitute(
#     #     page_title=title_str,
#     #     content_html=content_html_str,
#     # )
#     # with open(os.path.join(path, out_filename+'.html'), "w") as f:
#     #     f.write(final_html)
#     # print(f"{title_str} saved in {out_filename}")  
#     # mi= _menu_item_for_file(path,name="user_activity", href=out_filename+'.html')
#     # f_menu.append(mi)
#     # return f_menu
