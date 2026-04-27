translations = {
    "fa": {
        "profile": "پروفایل",
        "members": "اعضای",
        "date_from": "از",
        "date_to": "تا",
        "logout": "خروج",
        "Close": "بستن",
        "hint_text_InsertHazine": "هزینه را وارد کن",
        
        "edit_cost_formtitle": "ویرایش هزینه ها",
        "edit_cost_title": "عنوان",
        "edit_cost_date": "تاریخ",
        "edit_cost_hazine": "نوع هزینه",
        "edit_cost_member": "عضو",
        "edit_cost_price": "مبلغ",
        "edit_cost_curency": "ارز",
        "edit_cost_save": "ذخیره",
        "edit_cost_regect": "انصراف",

        "Sabt_hazine_empty_expense_title": "هنوز هزینه‌ای ثبت نشده",
        "Sabt_hazine_empty_expense_sub": "برای شروع، یک هزینه وارد کن"        ,
        
        "GantChart_pie": "دایره ای",
        "GantChart_Bar": "ستونی",
        "GantChart_Empty": "داده‌ای برای نمایش وجود ندارد",

        "Hazineha_hintserch": "جستجو در دسته‌ها...",
        "Hazineha_NameNew": "نام زیر دسته جدید",
        "Hazineha_CanNotFind": "موردی پیدا نشد",
        "Hazineha_title": "انتخاب نوع هزینه",
        "Hazineha_Select": "انتخاب",
        "Hazineha_Reject": "انضراف",
        "Hazineha_SubHazine": "زیر شاخه",
        "Hazineha_AllMember": "همه اعضا",
        "Hazine_SerchMember": "جستجوی نام یا نسبت",

        "Member_Title": "اعضا",
        "Member_Insert": "افزودن عضو",
        "Member_LableName": "نام",
        "Member_LableRelation": "نسبت",
        "Member_Save": "ذخیره",
        "Member_Cancel": "انصراف",
        "Member_LableEdit": "ویرایش",
        "Member_LableDelete": "حذف",

    },
    "en": {

        "profile": "Profile",
        "members": "Members",
        "date_from": "Fr",
        "date_to": "To",
        "logout": "Log Out",
        "Close": "Close",
        "hint_text_InsertHazine": "Enter your expense",

        "edit_cost_formtitle": "Edit Expense",
        "edit_cost_title": "Title",
        "edit_cost_date": "Date",
        "edit_cost_hazine": "Category",
        "edit_cost_member": "Member",
        "edit_cost_price": "Amount",
        "edit_cost_curency": "Currency",
        "edit_cost_save": "Save",
        "edit_cost_regect": "Cancel",

        "Sabt_hazine_empty_expense_title": "No expenses yet",
        "Sabt_hazine_empty_expense_sub": "Start by adding your first expense",

        "GantChart_pie": "Pie Chart",
        "GantChart_Bar": "Bar Chart",
        "GantChart_Empty": "No data available",

        "Hazineha_hintserch": "Search categories...",
        "Hazineha_NameNew": "New subcategory name",
        "Hazineha_CanNotFind": "No results found",
        "Hazineha_title": "Select Category",
        "Hazineha_Select": "Select",
        "Hazineha_Reject": "Cancel",
        "Hazineha_SubHazine": "Subcategory",
        "Hazineha_AllMember": "AllMember",
        "Hazine_SerchMember": "Serch Name or Relation",

        "Member_Title": "Family Members",
        "Member_Insert": "Add Member",
        "Member_LableName": "Name",
        "Member_LableRelation": "Relation",
        "Member_Save": "Save",
        "Member_Cancel": "Cancel",
        "Member_LableEdit": "Edit",
        "Member_LableDelete": "Delete"
    }
}

def t(page, key):
    if page.data is None:
        page.data = {}

    lang = page.data.get("lang", "fa")
    return translations.get(lang, {}).get(key, "")