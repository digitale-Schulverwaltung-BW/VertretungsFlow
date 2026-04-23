<?php
/**
 * Admin-Verwaltung für AbsenzFlow WordPress Plugin
 */

class AbsenzFlow_Admin {
    
    private static $instance = null;
    
    public static function get_instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        add_action('admin_menu', array($this, 'add_admin_menu'));
        add_action('admin_init', array($this, 'register_settings'));
    }
    
    /**
     * Fügt Admin-Menüpunkt hinzu
     */
    public function add_admin_menu() {
        add_menu_page(
            'AbsenzFlow',              // Page title
            'AbsenzFlow',              // Menu title
            'manage_options',          // Capability
            'absenzflow',              // Menu slug
            array($this, 'render_admin_page'), // Callback
            'dashicons-calendar-alt',  // Icon
            30                         // Position
        );
        
        // Untermenü: Einstellungen
        add_submenu_page(
            'absenzflow',
            'Einstellungen',
            'Einstellungen',
            'manage_options',
            'absenzflow-settings',
            array($this, 'render_settings_page')
        );
        
        // Untermenü: Rollenverwaltung
        add_submenu_page(
            'absenzflow',
            'Rollenverwaltung',
            'Rollenverwaltung',
            'manage_options',
            'absenzflow-roles',
            array($this, 'render_roles_page')
        );

        // Untermenü: WebUntis Cache
        add_submenu_page(
            'absenzflow',
            'WebUntis Cache',
            'WebUntis Cache',
            'manage_options',
            'absenzflow-cache',
            array($this, 'render_cache_page')
        );
    }
    
    /**
     * Registriert Plugin-Einstellungen
     */
    public function register_settings() {
        register_setting('absenzflow_options_group', 'absenzflow_options', array(
            'sanitize_callback' => array($this, 'sanitize_options')
        ));
        
        // Settings Section
        add_settings_section(
            'absenzflow_main_section',
            'API-Einstellungen',
            array($this, 'section_callback'),
            'absenzflow-settings'
        );
        
        // API URL Field
        add_settings_field(
            'api_url',
            'Backend API URL',
            array($this, 'api_url_field_callback'),
            'absenzflow-settings',
            'absenzflow_main_section'
        );

        // API Secret Field
        add_settings_field(
            'api_secret',
            'Backend API Secret',
            array($this, 'api_secret_field_callback'),
            'absenzflow-settings',
            'absenzflow_main_section'
        );

        // SSL Verify Field
        add_settings_field(
            'ssl_verify',
            'SSL-Zertifikat verifizieren',
            array($this, 'ssl_verify_field_callback'),
            'absenzflow-settings',
            'absenzflow_main_section'
        );

        // Permissions Section
        add_settings_section(
            'absenzflow_permissions_section',
            'Berechtigungen',
            array($this, 'permissions_section_callback'),
            'absenzflow-settings'
        );

        // Dept Heads Can Complete Field
        add_settings_field(
            'dept_heads_can_complete',
            'Abteilungsleitungen können erledigen',
            array($this, 'dept_heads_can_complete_field_callback'),
            'absenzflow-settings',
            'absenzflow_permissions_section'
        );
    }
    
    /**
     * Sanitize Options
     */
    public function sanitize_options($input) {
        $sanitized = array();

        if (isset($input['api_url'])) {
            $sanitized['api_url'] = esc_url_raw($input['api_url']);
        }

        if (isset($input['api_secret'])) {
            $sanitized['api_secret'] = sanitize_text_field($input['api_secret']);
        }

        // Checkbox: ssl_verify (default: true for security)
        $sanitized['ssl_verify'] = isset($input['ssl_verify']) ? 1 : 0;

        // Checkbox: dept_heads_can_complete
        $sanitized['dept_heads_can_complete'] = isset($input['dept_heads_can_complete']) ? 1 : 0;

        return $sanitized;
    }
    
    /**
     * Section Callback
     */
    public function section_callback() {
        echo '<p>Konfigurieren Sie die Verbindung zum AbsenzFlow Backend.</p>';
    }
    
    /**
     * API URL Field
     */
    public function api_url_field_callback() {
        $options = get_option('absenzflow_options');
        $api_url = isset($options['api_url']) ? $options['api_url'] : '';

        echo '<input type="text" name="absenzflow_options[api_url]" value="' . esc_attr($api_url) . '" class="regular-text" />';
        echo '<p class="description">Backend API URL <strong>mit /api Suffix</strong>, z.B. http://localhost:8000/api oder https://absenzflow.schule.de/api</p>';
    }

    /**
     * API Secret Field
     */
    public function api_secret_field_callback() {
        $options = get_option('absenzflow_options');
        $api_secret = isset($options['api_secret']) ? $options['api_secret'] : '';

        echo '<input type="password" name="absenzflow_options[api_secret]" value="' . esc_attr($api_secret) . '" class="regular-text" />';
        echo '<p class="description">Shared Secret für sichere Kommunikation mit dem Backend. Muss identisch mit WORDPRESS_PROXY_SECRET im Backend sein.</p>';
    }

    /**
     * SSL Verify Field
     */
    public function ssl_verify_field_callback() {
        $options = get_option('absenzflow_options');
        // Default to checked (SSL verified) when option is not yet set — secure by default
        $checked = !isset($options['ssl_verify']) || $options['ssl_verify'] ? 'checked' : '';

        echo '<label>';
        echo '<input type="checkbox" name="absenzflow_options[ssl_verify]" value="1" ' . $checked . ' />';
        echo ' SSL-Zertifikate bei Backend-Verbindungen prüfen';
        echo '</label>';
        echo '<p class="description">Empfohlen für Produktionsumgebungen. Deaktivieren Sie diese Option nur, wenn Sie selbstsignierte Zertifikate in Entwicklungsumgebungen verwenden.</p>';
    }

    /**
     * Permissions Section Callback
     */
    public function permissions_section_callback() {
        echo '<p>Konfigurieren Sie die Berechtigungen für verschiedene Rollen.</p>';
    }

    /**
     * Dept Heads Can Complete Field
     */
    public function dept_heads_can_complete_field_callback() {
        $options = get_option('absenzflow_options');
        $checked = isset($options['dept_heads_can_complete']) && $options['dept_heads_can_complete'] ? 'checked' : '';

        echo '<label>';
        echo '<input type="checkbox" name="absenzflow_options[dept_heads_can_complete]" value="1" ' . $checked . ' />';
        echo ' Abteilungsleitungen können Abwesenheiten als erledigt markieren';
        echo '</label>';
        echo '<p class="description">Wenn aktiviert, können Abteilungsleitungen Abwesenheiten direkt als erledigt markieren, ohne dass ein Vertretungsplaner sie erst eintragen muss.</p>';
    }

    /**
     * Render Admin Page (Dashboard)
     */
    public function render_admin_page() {
        ?>
        <div class="wrap">
            <h1>AbsenzFlow Dashboard</h1>
            <p>Willkommen im AbsenzFlow Verwaltungsbereich.</p>
            
            <div class="card">
                <h2>Schnellstart</h2>
                <ol>
                    <li>Konfigurieren Sie die <a href="<?php echo admin_url('admin.php?page=absenzflow-settings'); ?>">API-Einstellungen</a></li>
                    <li>Verwalten Sie <a href="<?php echo admin_url('admin.php?page=absenzflow-roles'); ?>">Benutzerrollen</a></li>
                    <li>Binden Sie AbsenzFlow mit dem Shortcode <code>[absenzflow]</code> ein</li>
                </ol>
            </div>
            
            <div class="card">
                <h2>Shortcode-Verwendung</h2>
                <p>Fügen Sie folgenden Shortcode zu einer Seite hinzu:</p>
                <pre><code>[absenzflow]</code></pre>
            </div>
        </div>
        <?php
    }
    
    /**
     * Render Settings Page
     */
    public function render_settings_page() {
        ?>
        <div class="wrap">
            <h1>AbsenzFlow Einstellungen</h1>
            <form method="post" action="options.php">
                <?php
                settings_fields('absenzflow_options_group');
                do_settings_sections('absenzflow-settings');
                submit_button();
                ?>
            </form>
        </div>
        <?php
    }
    
    /**
     * Render Roles Page
     */
    public function render_roles_page() {
        // Load current user roles from database
        global $wpdb;

        // Batch form submitted - save all role changes at once
        if (isset($_POST['absenzflow_batch_update_roles']) && check_admin_referer('absenzflow_roles_batch_update')) {
            $roles = isset($_POST['roles']) ? $_POST['roles'] : array();
            $webuntis_codes = isset($_POST['webuntis_codes']) ? $_POST['webuntis_codes'] : array();

            $updated_count = 0;

            foreach ($roles as $user_id => $role) {
                $user_id = intval($user_id);
                $role = sanitize_text_field($role);

                // Validate role - only allow known roles
                if (!in_array($role, ['teacher', 'dept_head', 'planner', 'admin'], true)) {
                    continue;
                }

                // Update role only if it changed
                $old_role = get_user_meta($user_id, 'absenzflow_role', true);
                if ($old_role !== $role) {
                    update_user_meta($user_id, 'absenzflow_role', $role);
                    $updated_count++;
                }

                // Update WebUntis code only if provided
                if (isset($webuntis_codes[$user_id])) {
                    $code = sanitize_text_field(trim($webuntis_codes[$user_id]));
                    $old_code = get_user_meta($user_id, 'absenzflow_webuntis_code', true);

                    if (!empty($code)) {
                        // Only update if code changed
                        if ($old_code !== $code) {
                            update_user_meta($user_id, 'absenzflow_webuntis_code', $code);
                            $updated_count++;
                        }
                    } else {
                        // Delete if empty and previously set
                        if ($old_code !== '') {
                            delete_user_meta($user_id, 'absenzflow_webuntis_code');
                            $updated_count++;
                        }
                    }
                }
            }

            // Display result message
            if ($updated_count > 0) {
                echo '<div class="notice notice-success"><p>' .
                     sprintf('Erfolgreich %d Änderung(en) gespeichert.', $updated_count) .
                     '</p></div>';
            } else {
                echo '<div class="notice notice-info"><p>Keine Änderungen vorgenommen.</p></div>';
            }
        }

        // Get all users
        $users = get_users();

        ?>
        <div class="wrap">
            <h1>AbsenzFlow Rollenverwaltung</h1>
            <p>Weisen Sie WordPress-Benutzern AbsenzFlow-Rollen zu.</p>

            <form method="post">
                <?php wp_nonce_field('absenzflow_roles_batch_update'); ?>

                <table class="wp-list-table widefat fixed striped">
                    <thead>
                        <tr>
                            <th>Benutzer</th>
                            <th>E-Mail</th>
                            <th>WordPress-Rolle</th>
                            <th>AbsenzFlow-Rolle</th>
                            <th>WebUntis-Kürzel</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($users as $user):
                            $current_role = get_user_meta($user->ID, 'absenzflow_role', true);
                            if (!$current_role) {
                                $current_role = 'teacher'; // Default
                            }
                            $webuntis_code = get_user_meta($user->ID, 'absenzflow_webuntis_code', true);
                        ?>
                        <tr>
                            <td><?php echo esc_html($user->display_name); ?></td>
                            <td><?php echo esc_html($user->user_email); ?></td>
                            <td><?php echo esc_html(implode(', ', $user->roles)); ?></td>
                            <td>
                                <select name="roles[<?php echo intval($user->ID); ?>]">
                                    <option value="teacher" <?php selected($current_role, 'teacher'); ?>>Lehrkraft</option>
                                    <option value="dept_head" <?php selected($current_role, 'dept_head'); ?>>Abteilungsleiter</option>
                                    <option value="planner" <?php selected($current_role, 'planner'); ?>>Vertretungsplaner</option>
                                    <option value="admin" <?php selected($current_role, 'admin'); ?>>Administrator</option>
                                </select>
                            </td>
                            <td>
                                <input type="text"
                                       name="webuntis_codes[<?php echo intval($user->ID); ?>]"
                                       value="<?php echo esc_attr($webuntis_code); ?>"
                                       placeholder="Kürzel"
                                       maxlength="20"
                                       style="width: 100px;">
                            </td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>

                <p class="submit">
                    <button type="submit" name="absenzflow_batch_update_roles" class="button button-primary">
                        Alle Änderungen speichern
                    </button>
                </p>
            </form>
        </div>
        <?php
    }

    /**
     * Rendert Cache-Verwaltungsseite
     */
    public function render_cache_page() {
        // Check permissions
        if (!current_user_can('manage_options')) {
            wp_die(__('You do not have sufficient permissions to access this page.'));
        }

        // Get API settings
        $options = get_option('absenzflow_options');
        $api_url = isset($options['api_url']) ? rtrim($options['api_url'], '/') : '';
        $api_secret = isset($options['api_secret']) ? $options['api_secret'] : '';

        if (empty($api_url) || empty($api_secret)) {
            echo '<div class="notice notice-error"><p>API URL oder Secret nicht konfiguriert. Bitte in den Einstellungen eintragen.</p></div>';
            return;
        }

        // Handle refresh action
        if (isset($_POST['refresh_cache']) && check_admin_referer('absenzflow_refresh_cache')) {
            $ssl_verify = !isset($options['ssl_verify']) || (bool)$options['ssl_verify'];
            $response = wp_remote_post($api_url . '/absences/admin/webuntis-cache/refresh', array(
                'headers' => array(
                    'Content-Type' => 'application/json',
                    'X-WordPress-Secret' => $api_secret,
                    'X-WordPress-User' => wp_get_current_user()->user_login,
                    'X-WordPress-Email' => wp_get_current_user()->user_email,
                    'X-WordPress-Role' => 'admin',
                ),
                'timeout' => 30,
                'sslverify' => $ssl_verify
            ));

            if (is_wp_error($response)) {
                echo '<div class="notice notice-error"><p>Fehler beim Aktualisieren des Cache: ' . esc_html($response->get_error_message()) . '</p></div>';
            } else {
                $body = wp_remote_retrieve_body($response);
                $result = json_decode($body, true);

                if ($result && isset($result['message'])) {
                    echo '<div class="notice notice-success"><p>' . esc_html($result['message']) . '</p></div>';
                } else {
                    echo '<div class="notice notice-error"><p>Cache aktualisiert, aber unerwartete Antwort erhalten.</p></div>';
                }
            }
        }

        // Get cache status
        $ssl_verify = !isset($options['ssl_verify']) || (bool)$options['ssl_verify'];
        $response = wp_remote_get($api_url . '/absences/admin/webuntis-cache/status', array(
            'headers' => array(
                'Content-Type' => 'application/json',
                'X-WordPress-Secret' => $api_secret,
                'X-WordPress-User' => wp_get_current_user()->user_login,
                'X-WordPress-Email' => wp_get_current_user()->user_email,
                'X-WordPress-Role' => 'admin',
            ),
            'timeout' => 15,
            'sslverify' => $ssl_verify
        ));

        $status = null;
        if (!is_wp_error($response)) {
            $body = wp_remote_retrieve_body($response);
            $status = json_decode($body, true);
        }

        ?>
        <div class="wrap">
            <h1>WebUntis Cache Verwaltung</h1>

            <div class="card">
                <h2>Performance-Optimierung</h2>
                <p>
                    WebUntis Stammdaten (Fächer, Klassen, Räume, Stundenraster) werden gecacht,
                    um die Absenzerstellung zu beschleunigen.
                </p>
                <p>
                    <strong>Cache-Gültigkeit:</strong> 7 Tage (konfigurierbar in .env)
                </p>
            </div>

            <div class="card">
                <h2>Cache-Status</h2>
                <?php if ($status && isset($status['cached_keys'])): ?>
                    <table class="widefat">
                        <thead>
                            <tr>
                                <th>Daten</th>
                                <th>Anzahl Einträge</th>
                                <th>Erstellt</th>
                                <th>Verfällt</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($status['cached_keys'] as $entry): ?>
                                <tr>
                                    <td><?php echo esc_html(str_replace('webuntis:', '', $entry['key'])); ?></td>
                                    <td><?php echo esc_html($entry['items_count']); ?></td>
                                    <td><?php echo esc_html($entry['created_at'] ? date('d.m.Y H:i', strtotime($entry['created_at'])) : '-'); ?></td>
                                    <td><?php echo esc_html($entry['expires_at'] ? date('d.m.Y H:i', strtotime($entry['expires_at'])) : 'Nie'); ?></td>
                                    <td>
                                        <?php if ($entry['is_expired']): ?>
                                            <span class="dashicons dashicons-warning" style="color: orange;"></span> Abgelaufen
                                        <?php else: ?>
                                            <span class="dashicons dashicons-yes" style="color: green;"></span> Gültig
                                        <?php endif; ?>
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                <?php else: ?>
                    <p>Noch keine Daten im Cache.</p>
                <?php endif; ?>
            </div>

            <div class="card">
                <h2>Cache Aktualisieren</h2>
                <p>
                    Verwenden Sie diese Funktion, wenn sich Stammdaten in WebUntis geändert haben
                    (z.B. neue Lehrkräfte, neue Räume, geändertes Stundenraster).
                </p>
                <form method="post">
                    <?php wp_nonce_field('absenzflow_refresh_cache'); ?>
                    <button type="submit" name="refresh_cache" class="button button-primary">
                        <span class="dashicons dashicons-update"></span>
                        WebUntis Stammdaten jetzt aktualisieren
                    </button>
                </form>
                <p class="description">
                    <strong>Hinweis:</strong> Der Cache wird beim nächsten Abruf automatisch neu befüllt.
                    Dies kann 5-10 Sekunden dauern.
                </p>
            </div>
        </div>
        <?php
    }
}
