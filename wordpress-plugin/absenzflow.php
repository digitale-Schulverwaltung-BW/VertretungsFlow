<?php
/**
 * Plugin Name: VertretungsFlow
 * Plugin URI: https://github.com/your-org/absenzflow
 * Description: Abwesenheitsmanagement für Schulen mit WebUntis-Integration
 * Version: 1.1.0
 * Author: Your School IT Team
 * Author URI: https://your-school.de
 * License: MIT
 * Text Domain: absenzflow
 */

// Verhindere direkten Zugriff
if (!defined('ABSPATH')) {
    exit;
}

// Plugin Konstanten
define('VERTRETUNGSFLOW_VERSION', '1.1.0');
define('VERTRETUNGSFLOW_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('VERTRETUNGSFLOW_PLUGIN_URL', plugin_dir_url(__FILE__));

/**
 * VertretungsFlow Plugin Hauptklasse
 */
class VertretungsFlow_Plugin {
    
    /**
     * Singleton Instanz
     */
    private static $instance = null;
    
    /**
     * Get Singleton Instance
     */
    public static function get_instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    /**
     * Constructor
     */
    private function __construct() {
        $this->load_dependencies();
        $this->register_hooks();
    }
    
    /**
     * Lade Abhängigkeiten
     */
    private function load_dependencies() {
        require_once VERTRETUNGSFLOW_PLUGIN_DIR . 'includes/class-migration.php';
        require_once VERTRETUNGSFLOW_PLUGIN_DIR . 'includes/class-admin.php';
        require_once VERTRETUNGSFLOW_PLUGIN_DIR . 'includes/class-shortcode.php';
        require_once VERTRETUNGSFLOW_PLUGIN_DIR . 'includes/class-api-proxy.php';
    }
    
    /**
     * Registriere WordPress Hooks
     */
    private function register_hooks() {
        // Daten-Migration von AbsenzFlow (Option, User-Meta); idempotent
        add_action('plugins_loaded', array('VertretungsFlow_Migration', 'run'), 1);

        // Aktivierung
        register_activation_hook(__FILE__, array($this, 'activate'));
        
        // Deaktivierung
        register_deactivation_hook(__FILE__, array($this, 'deactivate'));
        
        // Admin-Seite
        if (is_admin()) {
            VertretungsFlow_Admin::get_instance();
        }
        
        // Shortcode
        VertretungsFlow_Shortcode::get_instance();
        
        // API Proxy (für sichere Backend-Kommunikation)
        VertretungsFlow_API_Proxy::get_instance();
    }
    
    /**
     * Plugin Aktivierung
     */
    public function activate() {
        // Standardeinstellungen setzen
        $default_options = array(
            'api_url' => '',
            'enabled' => false
        );
        
        add_option('vertretungsflow_options', $default_options);
        
        // Flush Rewrite Rules
        flush_rewrite_rules();
    }
    
    /**
     * Plugin Deaktivierung
     */
    public function deactivate() {
        // Cleanup wenn nötig
        flush_rewrite_rules();
    }
}

/**
 * Plugin initialisieren
 */
function vertretungsflow_init() {
    return VertretungsFlow_Plugin::get_instance();
}

// Plugin starten
vertretungsflow_init();
