feat_extract = """
Conversation:
$CONVERSATION

Based on the conversation, extract the following:

1. OBJECTIVE: Overall goal of the client.
    - one simple and clear sentence that best represents the client's goal

2. WANTS: Positive features that would benefit the client in order to achieve the OBJECTIVE.
    - DO NOT include features that avoid, exclude or deny a certain aspect
    - you will be PUNISHED for starting feature name with "no" and "non"
    - name each feature using three words at most
    - handle one feature entity at a time, don't make features like "intel_or_amd" or "gaming_and_coding", focus on single features
    - use only lowercase letters and underscore(_) to represent spaces

3. AVOIDS: Negative features that hinder client's OBJECTIVE.
    - AGAIN, you will be PENALIZED for starting feature name with with "no" and "non"
    - same naming structure as PREFERENCE

Provide your result in following json format:
{
    "objective": the OBJECTIVE,
    "wants": [
        {"name:" name of feature },
        { next feature }
        ...
    ],
    "avoids": [
        {"name:" name of feature },
        { next feature }
        ...
    ],
}
"""


feat_match = """
You will recieve two lists of features.
One is from a client's request and the other is from a database.
The features in the client list are named without referencing the database.

Thus your job is to:
    1. for each feature in the client list, check for a database feature that has the same semantic meaning or could affect the client in similar way
    2. rename the feature to match its database counterpart

If change is unnecessary, just rewrite the features name.
If comparable feature does not exist in database, simply write {"idx": -1, "name": "none"} for feature_in_db.

Client Features:
$USER_PARAMETERS

Database Features:
{ idx: 0, name: is_microsoft }
{ idx: 1, name: is_gigabyte }
{ idx: 2, name: is_samsung }
{ idx: 3, name: is_huawei }
{ idx: 4, name: is_lenovo }
{ idx: 5, name: is_razer }
{ idx: 6, name: is_apple }
{ idx: 7, name: is_asus }
{ idx: 8, name: is_acer }
{ idx: 9, name: is_dell }
{ idx: 10, name: is_msi }
{ idx: 11, name: is_hp }
{ idx: 12, name: is_lg }
{ idx: 13, name: is_manufactured_2025 }
{ idx: 14, name: is_manufactured_2024 }
{ idx: 15, name: is_manufactured_2023 }
{ idx: 16, name: is_manufactured_2022 }
{ idx: 17, name: is_windows }
{ idx: 18, name: is_mac_os }
{ idx: 19, name: is_linux }
{ idx: 20, name: is_freedos }
{ idx: 21, name: is_office_use }
{ idx: 22, name: is_lecture_use }
{ idx: 23, name: is_gaming }
{ idx: 24, name: is_graphics_work }
{ idx: 25, name: is_video_editing }
{ idx: 26, name: is_portable_travel }
{ idx: 27, name: is_multimedia }
{ idx: 28, name: is_programming }
{ idx: 29, name: is_student_use }
{ idx: 30, name: is_silver }
{ idx: 31, name: is_white }
{ idx: 32, name: is_black }
{ idx: 33, name: is_gray }
{ idx: 34, name: is_gold }
{ idx: 35, name: is_pink }
{ idx: 36, name: is_blue }
{ idx: 37, name: is_green }
{ idx: 38, name: is_purple }
{ idx: 39, name: has_high_refreshrate }
{ idx: 40, name: is_cpu_intel }
{ idx: 41, name: is_cpu_amd }
{ idx: 42, name: is_cpu_qualcomm }
{ idx: 43, name: is_cpu_apple }
{ idx: 44, name: is_ddr4 }
{ idx: 45, name: is_ddr5 }
{ idx: 46, name: is_gpu_nvidia }
{ idx: 47, name: is_gpu_amd }
{ idx: 48, name: has_external_gpu }
{ idx: 49, name: has_internal_gpu }
{ idx: 50, name: has_hdmi }
{ idx: 51, name: has_thunderbolt3 }
{ idx: 52, name: has_thunderbolt4 }
{ idx: 53, name: has_usb_pd }
{ idx: 54, name: has_dp_alt }
{ idx: 55, name: has_sdcard_slot }
{ idx: 56, name: is_light }
{ idx: 57, name: is_heavy }
{ idx: 58, name: has_high_ram }
{ idx: 59, name: is_price_budget }
{ idx: 60, name: is_price_midrange }
{ idx: 61, name: is_price_premium }
{ idx: 62, name: is_price_highend }
{ idx: 63, name: battery_size }
{ idx: 64, name: screen_size }
{ idx: 65, name: screen_brightness }
{ idx: 66, name: weight }
{ idx: 67, name: ram_size }
{ idx: 68, name: num_usb_c }
{ idx: 69, name: num_usb_a }
{ idx: 70, name: screen_resolution }
{ idx: 71, name: storage_size }
{ idx: 72, name: price }

Provide your result in following json format:
{   
    "result": [
        {
            "feature": name of the feature in request,
            "feature_in_db": {
                "idx": index number of the feature in database
                "name": name of the feature in database
            }
        },
        {
            next feature
        },
        ...
    ]
}
"""

feat_categorize = """
Based on the client's request, feature extraction team has made a list of client parameters.
Your job is to label each features by carefully inspecting the client's request.

Also, mark the feature's "type" as "constraint" if the feature is make or break for the client.
Mark the feature's "type" as "objective" if the feature is not make or break for the client.

Look at the following example for further explanation.

Request: "I am allergic to peanuts. I like sour taste. Chicken would be nice but any kind of meat is fine."
Preference: [{"name": "sour"}, {"name": "has_chicken"}, {"name": "has_meat"}]
Dislikes: [{"name": "has_peanut"}]
Your result should be: {
    "result": [
     {"name": "is_sour", "type": "objective"},
     {"name": "has_chicken", "type": "objective"}, 
     {"name": "has_meat", "type": "objective"},
     {"name": "has_peanut", "type": "constraint"}
    ],
}

From the example, has_peanut's type is constraint because the client is allergic to peanut and it is dangerous to serve food with peanuts.
Others are objective because they match the client's preferences but it is not make or break for the client.

Finally, DO NOT label features that don't start with "has" or "is" as constraint.
If "price" is set as 'constraint' then any item that has a price value(all items) will be excluded!!

Now label each features given the Client's Request.

Conversation:
$CONVERSATION

Client's Features:

Preference: $WANTS
Dislike: $AVOIDS

Provide your result in following json format:
{   
    "result": [
        {
            "name": name of feature,
            "type": "objective" or "constraint"
        },
        {
            next feature
        },
        ...
    ],
}
"""