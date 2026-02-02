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
        
        // Wenn Form submitted
        if (isset($_POST['absenzflow_update_role']) && check_admin_referer('absenzflow_role_update')) {
            $user_id = intval($_POST['user_id']);
            $role = sanitize_text_field($_POST['absenzflow_role']);

            update_user_meta($user_id, 'absenzflow_role', $role);

            // WebUntis-Kürzel speichern
            if (isset($_POST['webuntis_code'])) {
                $code = sanitize_text_field(trim($_POST['webuntis_code']));

                if (!empty($code)) {
                    update_user_meta($user_id, 'absenzflow_webuntis_code', $code);
                } else {
                    delete_user_meta($user_id, 'absenzflow_webuntis_code');
                }
            }

            echo '<div class="notice notice-success"><p>Rolle erfolgreich aktualisiert.</p></div>';
        }
        
        // Get all users
        $users = get_users();
        
        ?>
        <div class="wrap">
            <h1>AbsenzFlow Rollenverwaltung</h1>
            <p>Weisen Sie WordPress-Benutzern AbsenzFlow-Rollen zu.</p>
            
            <table class="wp-list-table widefat fixed striped">
                <thead>
                    <tr>
                        <th>Benutzer</th>
                        <th>E-Mail</th>
                        <th>WordPress-Rolle</th>
                        <th>AbsenzFlow-Rolle</th>
                        <th>WebUntis-Kürzel</th>
                        <th>Aktion</th>
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
                            <form method="post" style="display: inline;">
                                <?php wp_nonce_field('absenzflow_role_update'); ?>
                                <input type="hidden" name="user_id" value="<?php echo $user->ID; ?>" />
                                <select name="absenzflow_role">
                                    <option value="teacher" <?php selected($current_role, 'teacher'); ?>>Lehrkraft</option>
                                    <option value="dept_head" <?php selected($current_role, 'dept_head'); ?>>Abteilungsleiter</option>
                                    <option value="planner" <?php selected($current_role, 'planner'); ?>>Vertretungsplaner</option>
                                    <option value="admin" <?php selected($current_role, 'admin'); ?>>Administrator</option>
                                </select>
                        </td>
                        <td>
                                <input type="text"
                                       name="webuntis_code"
                                       value="<?php echo esc_attr($webuntis_code); ?>"
                                       placeholder="Kürzel"
                                       maxlength="20"
                                       style="width: 100px;">
                        </td>
                        <td>
                                <button type="submit" name="absenzflow_update_role" class="button button-small">Speichern</button>
                            </form>
                        </td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
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

        // Handle refresh action
        if (isset($_POST['refresh_cache']) && check_admin_referer('absenzflow_refresh_cache')) {
            require_once plugin_dir_path(__FILE__) . 'class-api-proxy.php';
            $api_proxy = AbsenzFlow_API_Proxy::get_instance();
            $result = $api_proxy->request('POST', '/absences/admin/webuntis-cache/refresh');

            if ($result && !isset($result['error'])) {
                echo '<div class="notice notice-success"><p>WebUntis Cache wurde erfolgreich aktualisiert.</p></div>';
            } else {
                $error_msg = isset($result['error']) ? $result['error'] : 'Unbekannter Fehler';
                echo '<div class="notice notice-error"><p>Fehler beim Aktualisieren des Cache: ' . esc_html($error_msg) . '</p></div>';
            }
        }

        // Get cache status
        require_once plugin_dir_path(__FILE__) . 'class-api-proxy.php';
        $api_proxy = AbsenzFlow_API_Proxy::get_instance();
        $status = $api_proxy->request('GET', '/absences/admin/webuntis-cache/status');

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
