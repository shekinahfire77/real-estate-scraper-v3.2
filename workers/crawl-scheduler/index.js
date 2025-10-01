/**
 * Crawl Scheduler Worker
 * Manages crawl job scheduling and rate limiting
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    
    // Health check endpoint
    if (url.pathname === '/health') {
      return new Response('OK', { status: 200 });
    }

    // Schedule a crawl job
    if (url.pathname === '/schedule' && request.method === 'POST') {
      try {
        const body = await request.json();
        const { urls, priority = 'normal', source = 'redfin' } = body;

        // Store job in KV
        const jobId = crypto.randomUUID();
        const job = {
          id: jobId,
          urls,
          source,
          priority,
          status: 'queued',
          created_at: new Date().toISOString(),
          attempts: 0
        };

        await env.SCHEDULER_KV.put(`job:${jobId}`, JSON.stringify(job), {
          expirationTtl: 86400 // 24 hours
        });

        // Add to queue
        await env.DISPATCHER_KV.put(`queue:${priority}:${jobId}`, JSON.stringify({
          jobId,
          scheduledFor: new Date().toISOString()
        }));

        return new Response(JSON.stringify({ 
          jobId, 
          status: 'scheduled',
          urls_count: urls.length 
        }), {
          status: 201,
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (error) {
        return new Response(JSON.stringify({ error: error.message }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    // Get job status
    if (url.pathname.startsWith('/job/') && request.method === 'GET') {
      const jobId = url.pathname.split('/')[2];
      const job = await env.SCHEDULER_KV.get(`job:${jobId}`);
      
      if (!job) {
        return new Response('Job not found', { status: 404 });
      }

      return new Response(job, {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response('Not found', { status: 404 });
  },

  // Scheduled handler for cron jobs
  async scheduled(controller, env, ctx) {
    // Process queued jobs
    const keys = await env.DISPATCHER_KV.list({ prefix: 'queue:' });
    
    for (const key of keys.keys) {
      const job = await env.DISPATCHER_KV.get(key.name);
      if (job) {
        const jobData = JSON.parse(job);
        
        // Call Render API to process the job
        const response = await fetch('https://covenant-scraper-core.onrender.com/api/crawl', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': env.RENDER_API_KEY
          },
          body: JSON.stringify(jobData)
        });

        if (response.ok) {
          // Remove from queue
          await env.DISPATCHER_KV.delete(key.name);
          
          // Update job status
          const fullJob = await env.SCHEDULER_KV.get(`job:${jobData.jobId}`);
          if (fullJob) {
            const parsed = JSON.parse(fullJob);
            parsed.status = 'processing';
            parsed.started_at = new Date().toISOString();
            await env.SCHEDULER_KV.put(`job:${jobData.jobId}`, JSON.stringify(parsed));
          }
        }
      }
    }
  }
};
