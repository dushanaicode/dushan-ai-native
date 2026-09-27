def test_seeded_announcement_has_builtin_dictionary_label(system_database):
    _, _, connection = system_database
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT builtin FROM system_notification_notice "
            "WHERE code = 'system_announcement_publish' AND tenant_id = '1' AND deleted = 0"
        )
        assert cursor.fetchall() == ((1,),)
        cursor.execute(
            "SELECT label FROM system_dict_data "
            "WHERE dict_type = 'common_builtin_type' AND value = %s AND deleted = 0",
            ("1",),
        )
        assert cursor.fetchall() == (("内置",),)
