<?php
/**
 * Migration der Daten von AbsenzFlow nach VertretungsFlow
 *
 * Kopiert die alte Option und die User-Meta-Keys unter den neuen Namen.
 * Die alten Daten bleiben bewusst erhalten (Rollback moeglich) und werden
 * erst in einem spaeteren Release entfernt.
 */

if (!defined('ABSPATH')) {
    exit;
}

class VertretungsFlow_Migration {

    const DB_VERSION = '1.1.0';
    const DB_VERSION_OPTION = 'vertretungsflow_db_version';

    const OLD_OPTION = 'absenzflow_options';
    const NEW_OPTION = 'vertretungsflow_options';

    /**
     * Alter User-Meta-Key => neuer User-Meta-Key
     */
    const META_KEYS = array(
        'absenzflow_role' => 'vertretungsflow_role',
        'absenzflow_webuntis_code' => 'vertretungsflow_webuntis_code',
    );

    /**
     * Fuehrt die Migration einmalig aus (idempotent)
     */
    public static function run() {
        if (get_option(self::DB_VERSION_OPTION) === self::DB_VERSION) {
            return;
        }

        self::migrate_options();
        self::migrate_user_meta();

        update_option(self::DB_VERSION_OPTION, self::DB_VERSION);
    }

    /**
     * Kopiert die Plugin-Einstellungen (inkl. Proxy-Secret)
     */
    private static function migrate_options() {
        $old = get_option(self::OLD_OPTION);
        if ($old !== false && get_option(self::NEW_OPTION) === false) {
            add_option(self::NEW_OPTION, $old);
        }
    }

    /**
     * Kopiert Rollen und WebUntis-Kuerzel der Benutzer
     */
    private static function migrate_user_meta() {
        global $wpdb;

        foreach (self::META_KEYS as $old_key => $new_key) {
            $rows = $wpdb->get_results(
                $wpdb->prepare(
                    "SELECT user_id, meta_value FROM {$wpdb->usermeta} WHERE meta_key = %s",
                    $old_key
                )
            );
            foreach ($rows as $row) {
                // Bereits gesetzte neue Werte nie ueberschreiben
                if (metadata_exists('user', (int) $row->user_id, $new_key)) {
                    continue;
                }
                update_user_meta((int) $row->user_id, $new_key, maybe_unserialize($row->meta_value));
            }
        }
    }
}
