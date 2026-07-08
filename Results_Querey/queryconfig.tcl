*templatefileset "[ hm_info -appinfo ALTAIR_HOME ]/templates/feoutput/optistruct/optistruct"
*createstringarray 11 "OptiStruct " " " "ANSA " "PATRAN " "EXPAND_IDS_FOR_FORMULA_SETS "  "ASSIGNPROP_BYHMCOMMENTS" "CREATE_PART_HIERARCHY" "LOADCOLS_DISPLAY_SKIP " "VECTORCOLS_DISPLAY_SKIP "  "SYSTCOLS_DISPLAY_SKIP " "CONTACTSURF_DISPLAY_SKIP " 
*feinputwithdata2 "#optistruct\\optistruct" "C:/Users/lieve/OneDrive/Uni/Aerospace Master/1. Semester/Aerospace Strcutures/Assignment 2/AerospaceStructures_Assignment2/SuperPanel_AS_Project_Part2_submitted_start_3766785.fem" 0 0 0 0 0 1 11 1 0 
*createentity results
set resultid [hm_latestentityid results]
*setvalue results id=$resultid resultfiles="C:/Users/lieve/OneDrive/Uni/Aerospace Master/1. Semester/Aerospace Strcutures/Assignment 2/AerospaceStructures_Assignment2/Analysis1.op2"
*setvalue results id=$resultid init=1
hm_getresults id=$resultid xml="C:/Users/lieve/OneDrive/Uni/Aerospace Master/1. Semester/Aerospace Strcutures/Assignment 2/AerospaceStructures_Assignment2/Results_Querey/queryconfig.xml"
