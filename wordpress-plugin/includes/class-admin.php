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
    }
    
    /**
     * Sanitize Options
     */
    public function sanitize_options($input) {
        $sanitized = array();
        
        if (isset($input['api_url'])) {
            $sanitized['api_url'] = esc_url_raw($input['api_url']);
        }
        
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
        echo '<p class="description">z.B. http://localhost:8000 oder https://absenzflow.schule.de</p>';
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
                        <th>Aktion</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($users as $user): 
                        $current_role = get_user_meta($user->ID, 'absenzflow_role', true);
                        if (!$current_role) {
                            $current_role = 'teacher'; // Default
                        }
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
}
