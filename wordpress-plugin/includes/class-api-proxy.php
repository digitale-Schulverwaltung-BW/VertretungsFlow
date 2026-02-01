<?php
/**
 * API Proxy für sichere Backend-Kommunikation
 * Verhindert dass API-Credentials im Frontend exposed werden
 */

class AbsenzFlow_API_Proxy {
    
    private static $instance = null;
    
    public static function get_instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        add_action('rest_api_init', array($this, 'register_routes'));
        add_filter('rest_authentication_errors', array($this, 'allow_cookie_auth'));
    }

    /**
     * Allow cookie authentication for our endpoint
     */
    public function allow_cookie_auth($result) {
        // If already authenticated, return early
        if ($result === true || is_wp_error($result)) {
            return $result;
        }

        // Check if this is our endpoint
        if (strpos($_SERVER['REQUEST_URI'], '/absenzflow/v1/proxy') !== false) {
            // Check if user is logged in via WordPress session
            if (is_user_logged_in()) {
                // Allow cookie authentication for this endpoint
                return true;
            }
            // Debug: log why auth failed
            error_log('AbsenzFlow: Cookie auth failed - user not logged in. User ID: ' . get_current_user_id());
        }

        return $result;
    }
    
    /**
     * Registriert REST API Routes
     */
    public function register_routes() {
        // Proxy Route
        register_rest_route('absenzflow/v1', '/proxy', array(
            'methods' => 'POST',
            'callback' => array($this, 'proxy_request'),
            'permission_callback' => 'is_user_logged_in', // WordPress handles cookie auth + nonce validation
            'args' => array(
                'method' => array('required' => true),
                'endpoint' => array('required' => true),
            )
        ));

        // File Upload Proxy (separate endpoint for multipart/form-data)
        register_rest_route('absenzflow/v1', '/proxy/upload/(?P<absence_id>\d+)', array(
            'methods' => 'POST',
            'callback' => array($this, 'proxy_file_upload'),
            'permission_callback' => 'is_user_logged_in',
            'args' => array(
                'absence_id' => array(
                    'required' => true,
                    'validate_callback' => function($param) {
                        return is_numeric($param);
                    }
                ),
            )
        ));
    }
    
    /**
     * Proxy Request zum Backend
     */
    public function proxy_request($request) {
        // Debug logging
        error_log('AbsenzFlow Proxy: Request received');
        error_log('User logged in: ' . (is_user_logged_in() ? 'yes' : 'no'));
        error_log('User ID: ' . get_current_user_id());
        error_log('Current user: ' . (is_user_logged_in() ? wp_get_current_user()->user_login : 'none'));

        $options = get_option('absenzflow_options');
        $api_url = $options['api_url'];
        $api_secret = isset($options['api_secret']) ? $options['api_secret'] : '';

        if (empty($api_url)) {
            return new WP_Error('no_api_url', 'API URL nicht konfiguriert', array('status' => 500));
        }

        if (empty($api_secret)) {
            return new WP_Error('no_api_secret', 'API Secret nicht konfiguriert', array('status' => 500));
        }

        // Request-Daten
        $method = $request->get_param('method');
        $endpoint = $request->get_param('endpoint');
        $body = $request->get_param('body');
        $params = $request->get_param('params');
        $token = $request->get_param('token');

        // Request an Backend
        $url = rtrim($api_url, '/') . '/' . ltrim($endpoint, '/');

        // Query params für GET-Requests
        if (!empty($params) && is_array($params)) {
            $url = add_query_arg($params, $url);
        }

        // Current WordPress user
        $current_user = wp_get_current_user();

        // Read settings
        $dept_heads_can_complete = isset($options['dept_heads_can_complete']) && $options['dept_heads_can_complete'] ? '1' : '0';

        $args = array(
            'method' => strtoupper($method),
            'headers' => array(
                'Content-Type' => 'application/json',
                'X-WordPress-Secret' => $api_secret,
                'X-WordPress-User' => $current_user->user_login,
                'X-WordPress-Email' => $current_user->user_email,
                'X-WordPress-Name' => $current_user->display_name,
                'X-WordPress-Role' => $this->map_wp_role_to_absenzflow($current_user),
                'X-WordPress-WebUntis-Code' => get_user_meta($current_user->ID, 'absenzflow_webuntis_code', true),
                'X-WordPress-Dept-Heads-Can-Complete' => $dept_heads_can_complete
            ),
            'timeout' => 30,
            'sslverify' => false // Allow self-signed certs in development
        );

        // JWT Token hinzufügen falls vorhanden (für direkte Backend-Auth)
        if (!empty($token)) {
            $args['headers']['Authorization'] = 'Bearer ' . $token;
        }

        // Body hinzufügen bei POST/PUT/PATCH
        if (in_array(strtoupper($method), array('POST', 'PUT', 'PATCH')) && !empty($body)) {
            $args['body'] = json_encode($body);
        }

        // Request ausführen
        $response = wp_remote_request($url, $args);

        if (is_wp_error($response)) {
            return new WP_Error('proxy_error', $response->get_error_message(), array('status' => 500));
        }

        $status_code = wp_remote_retrieve_response_code($response);
        $response_body = wp_remote_retrieve_body($response);

        // Response zurückgeben
        return new WP_REST_Response(
            json_decode($response_body, true),
            $status_code
        );
    }

    /**
     * Proxy File Upload (multipart/form-data)
     */
    public function proxy_file_upload($request) {
        error_log('AbsenzFlow File Upload Proxy: Request received');
        error_log('User logged in: ' . (is_user_logged_in() ? 'yes' : 'no'));
        error_log('User ID: ' . get_current_user_id());

        $options = get_option('absenzflow_options');
        $api_url = $options['api_url'];
        $api_secret = isset($options['api_secret']) ? $options['api_secret'] : '';

        if (empty($api_url)) {
            return new WP_Error('no_api_url', 'API URL nicht konfiguriert', array('status' => 500));
        }

        if (empty($api_secret)) {
            return new WP_Error('no_api_secret', 'API Secret nicht konfiguriert', array('status' => 500));
        }

        // Get absence_id from URL parameter
        $absence_id = $request->get_param('absence_id');

        // Check if file was uploaded
        if (empty($_FILES) || !isset($_FILES['file'])) {
            return new WP_Error('no_file', 'Keine Datei hochgeladen', array('status' => 400));
        }

        $file = $_FILES['file'];

        // Validate upload
        if ($file['error'] !== UPLOAD_ERR_OK) {
            return new WP_Error('upload_error', 'Fehler beim Hochladen: ' . $file['error'], array('status' => 400));
        }

        // Current WordPress user
        $current_user = wp_get_current_user();
        $dept_heads_can_complete = isset($options['dept_heads_can_complete']) && $options['dept_heads_can_complete'] ? '1' : '0';

        // Build backend URL
        $url = rtrim($api_url, '/') . '/absences/' . $absence_id . '/attachments';

        // Prepare multipart request using cURL (wp_remote_request doesn't handle files well)
        $ch = curl_init($url);

        // Create CURLFile for the upload
        $curl_file = new CURLFile($file['tmp_name'], $file['type'], $file['name']);

        // Multipart form data
        $post_data = array('file' => $curl_file);

        // Headers
        $headers = array(
            'X-WordPress-Secret: ' . $api_secret,
            'X-WordPress-User: ' . $current_user->user_login,
            'X-WordPress-Email: ' . $current_user->user_email,
            'X-WordPress-Name: ' . $current_user->display_name,
            'X-WordPress-Role: ' . $this->map_wp_role_to_absenzflow($current_user),
            'X-WordPress-WebUntis-Code: ' . get_user_meta($current_user->ID, 'absenzflow_webuntis_code', true),
            'X-WordPress-Dept-Heads-Can-Complete: ' . $dept_heads_can_complete
        );

        curl_setopt_array($ch, array(
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $post_data,
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_SSL_VERIFYPEER => false, // Allow self-signed certs
            CURLOPT_TIMEOUT => 30
        ));

        $response_body = curl_exec($ch);
        $status_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curl_error = curl_error($ch);
        curl_close($ch);

        if ($curl_error) {
            error_log('AbsenzFlow File Upload: cURL error: ' . $curl_error);
            return new WP_Error('curl_error', $curl_error, array('status' => 500));
        }

        error_log('AbsenzFlow File Upload: Response status: ' . $status_code);
        error_log('AbsenzFlow File Upload: Response body: ' . substr($response_body, 0, 200));

        // Return response
        return new WP_REST_Response(
            json_decode($response_body, true),
            $status_code
        );
    }

    /**
     * Holt AbsenzFlow-Rolle aus User Meta
     *
     * @param WP_User $user WordPress User Objekt
     * @return string AbsenzFlow Rolle (admin/teacher/dept_head/planner)
     */
    private function map_wp_role_to_absenzflow($user) {
        // Rolle aus User Meta laden (wird über Rollenverwaltung gesetzt)
        $role = get_user_meta($user->ID, 'absenzflow_role', true);

        // Fallback zu 'teacher' wenn keine Rolle gesetzt
        if (empty($role)) {
            return 'teacher';
        }

        return $role;
    }
}
