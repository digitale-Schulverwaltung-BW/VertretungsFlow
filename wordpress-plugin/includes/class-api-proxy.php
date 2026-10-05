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

        // Check if this is one of our endpoints
        $uri = $_SERVER['REQUEST_URI'];
        if (
            strpos($uri, '/absenzflow/v1/proxy') !== false ||
            strpos($uri, '/absenzflow/v1/teachers') !== false
        ) {
            // Check if user is logged in via WordPress session
            if (is_user_logged_in()) {
                // Allow cookie authentication for this endpoint
                return true;
            }
            // Debug: log why auth failed
            if (defined('WP_DEBUG') && WP_DEBUG) {
                error_log('VertretungsFlow: Cookie auth failed - user not logged in. User ID: ' . get_current_user_id());
            }
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

        // File Download Proxy (auth-protected download)
        register_rest_route('absenzflow/v1', '/proxy/download/(?P<absence_id>\d+)/(?P<attachment_id>\d+)', array(
            'methods' => 'GET',
            'callback' => array($this, 'proxy_file_download'),
            'permission_callback' => 'is_user_logged_in',
            'args' => array(
                'absence_id' => array(
                    'required' => true,
                    'validate_callback' => function($param) {
                        return is_numeric($param);
                    }
                ),
                'attachment_id' => array(
                    'required' => true,
                    'validate_callback' => function($param) {
                        return is_numeric($param);
                    }
                ),
            )
        ));

        // Teachers endpoint (returns WP users with WebUntis code, for admin teacher selection)
        register_rest_route('absenzflow/v1', '/teachers', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_teachers'),
            'permission_callback' => function() {
                // Only admins (users with absenzflow_role = 'admin') may query this
                if (!is_user_logged_in()) {
                    return false;
                }
                $role = get_user_meta(get_current_user_id(), 'absenzflow_role', true);
                return $role === 'admin';
            },
        ));

        // PDF Form Download Proxy (auth-protected PDF download)
        register_rest_route('absenzflow/v1', '/proxy/pdf/(?P<absence_id>\d+)/(?P<form_type>[a-z_]+)', array(
            'methods' => 'GET',
            'callback' => array($this, 'proxy_pdf_download'),
            'permission_callback' => 'is_user_logged_in',
            'args' => array(
                'absence_id' => array(
                    'required' => true,
                    'validate_callback' => function($param) {
                        return is_numeric($param);
                    }
                ),
                'form_type' => array(
                    'required' => true,
                    'validate_callback' => function($param) {
                        return preg_match('/^[a-z_]+$/', $param);
                    }
                ),
            )
        ));
    }
    
    /**
     * Proxy Request zum Backend
     */
    public function proxy_request($request) {
        // Debug logging (only when WP_DEBUG is enabled)
        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('VertretungsFlow Proxy: Request received');
            error_log('User logged in: ' . (is_user_logged_in() ? 'yes' : 'no'));
            error_log('User ID: ' . get_current_user_id());
            error_log('Current user: ' . (is_user_logged_in() ? wp_get_current_user()->user_login : 'none'));
        }

        $options = get_option('absenzflow_options');
        $api_url = $options['api_url'];
        $api_secret = isset($options['api_secret']) ? $options['api_secret'] : '';

        // Security: only log whether the secret is configured, never its value
        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('VertretungsFlow Proxy: API Secret configured: ' . (!empty($api_secret) ? 'yes' : 'NO'));
        }

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

        // Security: Validate endpoint against allowlist to prevent SSRF
        $endpoint = ltrim($endpoint, '/');
        $allowed_prefixes = array('absences', 'auth', 'admin', 'pdf-forms');
        $is_allowed = false;
        foreach ($allowed_prefixes as $prefix) {
            if (strpos($endpoint, $prefix) === 0) {
                $is_allowed = true;
                break;
            }
        }
        if (!$is_allowed || strpos($endpoint, '..') !== false || strpos($endpoint, '://') !== false) {
            return new WP_Error('invalid_endpoint', 'Invalid API endpoint', array('status' => 400));
        }

        // Request an Backend
        $url = rtrim($api_url, '/') . '/' . $endpoint;

        // Query params für GET-Requests
        if (!empty($params) && is_array($params)) {
            $url = add_query_arg($params, $url);
        }

        // Current WordPress user
        $current_user = wp_get_current_user();

        // Read settings
        $dept_heads_can_complete = isset($options['dept_heads_can_complete']) && $options['dept_heads_can_complete'] ? '1' : '0';

        // URL-encode names to handle UTF-8 characters (äöüß) in HTTP headers
        $first_name = get_user_meta($current_user->ID, 'first_name', true);
        $last_name = get_user_meta($current_user->ID, 'last_name', true);

        $args = array(
            'method' => strtoupper($method),
            'headers' => array(
                'Content-Type' => 'application/json',
                'X-WordPress-Secret' => $api_secret,
                'X-WordPress-User' => $current_user->user_login,
                'X-WordPress-Email' => $current_user->user_email,
                'X-WordPress-Name' => $current_user->display_name,
                'X-WordPress-First-Name' => rawurlencode($first_name),
                'X-WordPress-Last-Name' => rawurlencode($last_name),
                'X-WordPress-Role' => $this->map_wp_role_to_absenzflow($current_user),
                'X-WordPress-WebUntis-Code' => rawurlencode(get_user_meta($current_user->ID, 'absenzflow_webuntis_code', true)),
                'X-WordPress-Dept-Heads-Can-Complete' => $dept_heads_can_complete
            ),
            'timeout' => 30,
            'sslverify' => $this->get_ssl_verify()
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
        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('VertretungsFlow Proxy: Calling backend URL: ' . $url);
        }
        $response = wp_remote_request($url, $args);

        if (is_wp_error($response)) {
            error_log('VertretungsFlow Proxy: WP Error: ' . $response->get_error_message());
            return new WP_Error('proxy_error', $response->get_error_message(), array('status' => 500));
        }

        $status_code = wp_remote_retrieve_response_code($response);
        $response_body = wp_remote_retrieve_body($response);

        // Debug: Log response (only when WP_DEBUG is enabled)
        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('VertretungsFlow Proxy: Backend response status: ' . $status_code);
            if ($status_code >= 400) {
                error_log('VertretungsFlow Proxy: Backend error response: ' . substr($response_body, 0, 200));
            }
        }

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
        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('VertretungsFlow File Upload Proxy: Request received');
            error_log('User logged in: ' . (is_user_logged_in() ? 'yes' : 'no'));
            error_log('User ID: ' . get_current_user_id());
        }

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

        // URL-encode names to handle UTF-8 characters (äöüß) in HTTP headers
        $first_name = get_user_meta($current_user->ID, 'first_name', true);
        $last_name = get_user_meta($current_user->ID, 'last_name', true);

        // Headers
        $headers = array(
            'X-WordPress-Secret: ' . $api_secret,
            'X-WordPress-User: ' . $current_user->user_login,
            'X-WordPress-Email: ' . $current_user->user_email,
            'X-WordPress-Name: ' . $current_user->display_name,
            'X-WordPress-First-Name: ' . rawurlencode($first_name),
            'X-WordPress-Last-Name: ' . rawurlencode($last_name),
            'X-WordPress-Role: ' . $this->map_wp_role_to_absenzflow($current_user),
            'X-WordPress-WebUntis-Code: ' . rawurlencode(get_user_meta($current_user->ID, 'absenzflow_webuntis_code', true)),
            'X-WordPress-Dept-Heads-Can-Complete: ' . $dept_heads_can_complete
        );

        curl_setopt_array($ch, array(
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $post_data,
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_SSL_VERIFYPEER => $this->get_ssl_verify(),
            CURLOPT_TIMEOUT => 30
        ));

        $response_body = curl_exec($ch);
        $status_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curl_error = curl_error($ch);
        curl_close($ch);

        if ($curl_error) {
            error_log('VertretungsFlow File Upload: cURL error: ' . $curl_error);
            return new WP_Error('curl_error', $curl_error, array('status' => 500));
        }

        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('VertretungsFlow File Upload: Response status: ' . $status_code);
            error_log('VertretungsFlow File Upload: Response body: ' . substr($response_body, 0, 200));
        }

        // Return response
        return new WP_REST_Response(
            json_decode($response_body, true),
            $status_code
        );
    }

    /**
     * Proxy File Download (streaming with auth)
     */
    public function proxy_file_download($request) {
        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('VertretungsFlow File Download Proxy: Request received');
        }

        $options = get_option('absenzflow_options');
        $api_url = $options['api_url'];
        $api_secret = isset($options['api_secret']) ? $options['api_secret'] : '';

        if (empty($api_url) || empty($api_secret)) {
            return new WP_Error('config_error', 'API nicht konfiguriert', array('status' => 500));
        }

        // Get parameters
        $absence_id = $request->get_param('absence_id');
        $attachment_id = $request->get_param('attachment_id');

        // Current WordPress user
        $current_user = wp_get_current_user();
        $dept_heads_can_complete = isset($options['dept_heads_can_complete']) && $options['dept_heads_can_complete'] ? '1' : '0';

        // Build backend URL
        $url = rtrim($api_url, '/') . '/absences/' . $absence_id . '/attachments/' . $attachment_id;

        // URL-encode names to handle UTF-8 characters (äöüß) in HTTP headers
        $first_name = get_user_meta($current_user->ID, 'first_name', true);
        $last_name = get_user_meta($current_user->ID, 'last_name', true);

        // Headers
        $headers = array(
            'X-WordPress-Secret: ' . $api_secret,
            'X-WordPress-User: ' . $current_user->user_login,
            'X-WordPress-Email: ' . $current_user->user_email,
            'X-WordPress-Name: ' . $current_user->display_name,
            'X-WordPress-First-Name: ' . rawurlencode($first_name),
            'X-WordPress-Last-Name: ' . rawurlencode($last_name),
            'X-WordPress-Role: ' . $this->map_wp_role_to_absenzflow($current_user),
            'X-WordPress-WebUntis-Code: ' . rawurlencode(get_user_meta($current_user->ID, 'absenzflow_webuntis_code', true)),
            'X-WordPress-Dept-Heads-Can-Complete: ' . $dept_heads_can_complete
        );

        // Use cURL for streaming
        $ch = curl_init($url);
        curl_setopt_array($ch, array(
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_SSL_VERIFYPEER => $this->get_ssl_verify(),
            CURLOPT_TIMEOUT => 60,
            CURLOPT_HEADER => true // Include headers in output
        ));

        $response = curl_exec($ch);
        $status_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        curl_close($ch);

        // Split headers and body
        $headers_str = substr($response, 0, $header_size);
        $body = substr($response, $header_size);

        // If error, return JSON error
        if ($status_code !== 200) {
            return new WP_REST_Response(
                json_decode($body, true),
                $status_code
            );
        }

        // Extract Content-Type and Content-Disposition from headers
        $content_type = 'application/octet-stream';
        $content_disposition = '';

        foreach (explode("\r\n", $headers_str) as $header) {
            if (stripos($header, 'Content-Type:') === 0) {
                $content_type = trim(substr($header, 13));
            }
            if (stripos($header, 'Content-Disposition:') === 0) {
                $content_disposition = trim(substr($header, 20));
            }
        }

        // Stream file back to browser
        header('Content-Type: ' . $content_type);
        if ($content_disposition) {
            header('Content-Disposition: ' . $content_disposition);
        }
        header('Content-Length: ' . strlen($body));
        echo $body;
        exit;
    }

    /**
     * Proxy PDF Form Download (streaming with auth)
     */
    public function proxy_pdf_download($request) {
        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('VertretungsFlow PDF Download Proxy: Request received');
        }

        $options = get_option('absenzflow_options');
        $api_url = $options['api_url'];
        $api_secret = isset($options['api_secret']) ? $options['api_secret'] : '';

        if (empty($api_url) || empty($api_secret)) {
            return new WP_Error('config_error', 'API nicht konfiguriert', array('status' => 500));
        }

        // Get parameters
        $absence_id = $request->get_param('absence_id');
        $form_type = $request->get_param('form_type');

        // Current WordPress user
        $current_user = wp_get_current_user();
        $dept_heads_can_complete = isset($options['dept_heads_can_complete']) && $options['dept_heads_can_complete'] ? '1' : '0';

        // Build backend URL
        $url = rtrim($api_url, '/') . '/absences/' . $absence_id . '/pdf-forms/' . $form_type;

        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('VertretungsFlow PDF Download: URL: ' . $url);
        }

        // URL-encode names to handle UTF-8 characters (äöüß) in HTTP headers
        $first_name = get_user_meta($current_user->ID, 'first_name', true);
        $last_name = get_user_meta($current_user->ID, 'last_name', true);

        // Headers
        $headers = array(
            'X-WordPress-Secret: ' . $api_secret,
            'X-WordPress-User: ' . $current_user->user_login,
            'X-WordPress-Email: ' . $current_user->user_email,
            'X-WordPress-Name: ' . $current_user->display_name,
            'X-WordPress-First-Name: ' . rawurlencode($first_name),
            'X-WordPress-Last-Name: ' . rawurlencode($last_name),
            'X-WordPress-Role: ' . $this->map_wp_role_to_absenzflow($current_user),
            'X-WordPress-WebUntis-Code: ' . rawurlencode(get_user_meta($current_user->ID, 'absenzflow_webuntis_code', true)),
            'X-WordPress-Dept-Heads-Can-Complete: ' . $dept_heads_can_complete
        );

        // Use cURL for streaming
        $ch = curl_init($url);
        curl_setopt_array($ch, array(
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_SSL_VERIFYPEER => $this->get_ssl_verify(),
            CURLOPT_TIMEOUT => 60,
            CURLOPT_HEADER => true // Include headers in output
        ));

        $response = curl_exec($ch);
        $status_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        $curl_error = curl_error($ch);
        curl_close($ch);

        if ($curl_error) {
            error_log('VertretungsFlow PDF Download: cURL error: ' . $curl_error);
            return new WP_Error('curl_error', $curl_error, array('status' => 500));
        }

        // Split headers and body
        $headers_str = substr($response, 0, $header_size);
        $body = substr($response, $header_size);

        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('VertretungsFlow PDF Download: Status: ' . $status_code . ', Body size: ' . strlen($body));
        }

        // If error, return JSON error
        if ($status_code !== 200) {
            if (defined('WP_DEBUG') && WP_DEBUG) {
                error_log('VertretungsFlow PDF Download: Error response: ' . substr($body, 0, 200));
            }
            return new WP_REST_Response(
                json_decode($body, true),
                $status_code
            );
        }

        // Extract Content-Type and Content-Disposition from headers
        $content_type = 'application/pdf';
        $content_disposition = '';

        foreach (explode("\r\n", $headers_str) as $header) {
            if (stripos($header, 'Content-Type:') === 0) {
                $content_type = trim(substr($header, 13));
            }
            if (stripos($header, 'Content-Disposition:') === 0) {
                $content_disposition = trim(substr($header, 20));
            }
        }

        // Stream PDF back to browser
        header('Content-Type: ' . $content_type);
        if ($content_disposition) {
            header('Content-Disposition: ' . $content_disposition);
        }
        header('Content-Length: ' . strlen($body));
        echo $body;
        exit;
    }

    /**
     * Returns all WP users who have a VertretungsFlow WebUntis code set.
     * Used by the admin teacher-selection combobox when creating an absence on behalf of another teacher.
     *
     * @return WP_REST_Response JSON array of {username, full_name, email, webuntis_code}
     */
    public function get_teachers() {
        $users = get_users(array(
            'meta_key'     => 'absenzflow_webuntis_code',
            'meta_value'   => '',
            'meta_compare' => '!=',
            'fields'       => 'all',
        ));

        $result = array();
        foreach ($users as $user) {
            $first_name = get_user_meta($user->ID, 'first_name', true);
            $last_name  = get_user_meta($user->ID, 'last_name', true);
            if ($first_name && $last_name) {
                $full_name = $first_name . ' ' . $last_name;
            } elseif ($user->display_name && $user->display_name !== $user->user_login) {
                $full_name = $user->display_name;
            } else {
                $full_name = $user->user_login;
            }
            $result[] = array(
                'username'      => $user->user_login,
                'full_name'     => $full_name,
                'email'         => $user->user_email,
                'webuntis_code' => get_user_meta($user->ID, 'absenzflow_webuntis_code', true),
            );
        }

        return new WP_REST_Response($result, 200);
    }

    /**
     * Returns whether SSL certificate verification is enabled.
     * Defaults to true (secure) when the option has not been explicitly set.
     *
     * @return bool
     */
    private function get_ssl_verify() {
        $options = get_option('absenzflow_options');
        return !isset($options['ssl_verify']) || (bool)$options['ssl_verify'];
    }

    /**
     * Holt VertretungsFlow-Rolle aus User Meta
     *
     * @param WP_User $user WordPress User Objekt
     * @return string VertretungsFlow Rolle (admin/teacher/dept_head/planner)
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
