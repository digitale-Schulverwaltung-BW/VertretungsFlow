<?php
/**
 * Plugin Name: AbsenzFlow
 * Plugin URI: https://github.com/your-org/absenzflow
 * Description: Abwesenheitsmanagement für Schulen mit WebUntis-Integration
 * Version: 1.0.1
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
define('ABSENZFLOW_VERSION', '1.0.1');
define('ABSENZFLOW_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('ABSENZFLOW_PLUGIN_URL', plugin_dir_url(__FILE__));

/**
 * AbsenzFlow Plugin Hauptklasse
 */
class AbsenzFlow_Plugin {
    
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
        require_once ABSENZFLOW_PLUGIN_DIR . 'includes/class-admin.php';
        require_once ABSENZFLOW_PLUGIN_DIR . 'includes/class-shortcode.php';
        require_once ABSENZFLOW_PLUGIN_DIR . 'includes/class-api-proxy.php';
    }
    
    /**
     * Registriere WordPress Hooks
     */
    private function register_hooks() {
        // Aktivierung
        register_activation_hook(__FILE__, array($this, 'activate'));
        
        // Deaktivierung
        register_deactivation_hook(__FILE__, array($this, 'deactivate'));
        
        // Admin-Seite
        if (is_admin()) {
            AbsenzFlow_Admin::get_instance();
        }
        
        // Shortcode
        AbsenzFlow_Shortcode::get_instance();
        
        // API Proxy (für sichere Backend-Kommunikation)
        AbsenzFlow_API_Proxy::get_instance();
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
        
        add_option('absenzflow_options', $default_options);
        
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
function absenzflow_init() {
    return AbsenzFlow_Plugin::get_instance();
}

// Plugin starten
absenzflow_init();
