create index if not exists idx_checkins_gym_result_date
    on public.checkins (gym_id, result, checkin_at desc);

create index if not exists idx_checkins_membership
    on public.checkins (membership_id);

create or replace function public.get_attendance_statistics(
    p_gym_id uuid,
    p_days integer default 30
)
returns jsonb
language plpgsql
stable
security invoker
set search_path = public
as $$
declare
    v_today date := public.gymsoft_today();
    v_days integer := least(
        greatest(coalesce(p_days, 30), 7),
        90
    );
    v_result jsonb;
begin
    with bounds as (
        select
            v_today as today_date,
            v_today - (v_days - 1) as period_start,
            v_today - ((v_days * 2) - 1) as previous_start,
            v_today - v_days as previous_end,
            date_trunc(
                'week',
                v_today::timestamp
            )::date as week_start,
            date_trunc(
                'month',
                v_today::timestamp
            )::date as month_start,
            v_today - (least(v_days, 30) - 1) as chart_start,
            least(
                v_today - ((v_days * 2) - 1),
                v_today - 29,
                date_trunc(
                    'week',
                    v_today::timestamp
                )::date,
                date_trunc(
                    'month',
                    v_today::timestamp
                )::date
            ) as fetch_start
    ),
    raw_checkins as (
        select
            c.id,
            c.client_id,
            c.membership_id,
            c.checkin_at at time zone 'America/Bogota'
                as local_at,
            cl.document,
            trim(
                concat_ws(
                    ' ',
                    cl.first_name,
                    cl.last_name
                )
            ) as client_name,
            coalesce(p.name, 'Sin plan') as plan_name,
            coalesce(
                m.entry_limit,
                p.entry_limit
            ) as entry_limit
        from public.checkins c
        join public.clients cl
          on cl.id = c.client_id
         and cl.gym_id = c.gym_id
        left join public.memberships m
          on m.id = c.membership_id
         and m.gym_id = c.gym_id
        left join public.plans p
          on p.id = m.plan_id
         and p.gym_id = c.gym_id
        cross join bounds b
        where c.gym_id = p_gym_id
          and c.result = 'PERMITIDA'
          and c.checkin_at >= (
              b.fetch_start::timestamp
              at time zone 'America/Bogota'
          )
          and c.checkin_at < (
              (b.today_date + 1)::timestamp
              at time zone 'America/Bogota'
          )
    ),
    classified as (
        select
            r.*,
            r.local_at::date as local_day,
            case
                when lower(r.plan_name) like '%tiquet%'
                     or coalesce(r.entry_limit, 0) > 1
                    then 'Tiquetera'
                when coalesce(r.entry_limit, 0) = 1
                     or lower(r.plan_name) ~
                        '(sesion|sesión|diario|día|dia|visita)'
                    then 'Sesión'
                when r.plan_name = 'Sin plan'
                    then 'Sin plan'
                else 'Mensualidad'
            end as plan_type
        from raw_checkins r
    ),
    period_rows as (
        select c.*
        from classified c
        cross join bounds b
        where c.local_day between
            b.period_start and b.today_date
    ),
    previous_rows as (
        select c.*
        from classified c
        cross join bounds b
        where c.local_day between
            b.previous_start and b.previous_end
    ),
    metric_values as (
        select
            count(*) filter (
                where c.local_day = b.today_date
            ) as today_entries,
            count(distinct c.client_id) filter (
                where c.local_day = b.today_date
            ) as today_unique,
            count(*) filter (
                where c.local_day between
                    b.week_start and b.today_date
            ) as week_entries,
            count(distinct c.client_id) filter (
                where c.local_day between
                    b.week_start and b.today_date
            ) as week_unique,
            count(*) filter (
                where c.local_day between
                    b.month_start and b.today_date
            ) as month_entries,
            count(distinct c.client_id) filter (
                where c.local_day between
                    b.month_start and b.today_date
            ) as month_unique,
            (
                select count(*)
                from period_rows
            ) as period_entries,
            (
                select count(distinct client_id)
                from period_rows
            ) as period_unique,
            (
                select count(*)
                from previous_rows
            ) as previous_entries
        from bounds b
        left join classified c on true
        group by
            b.today_date,
            b.week_start,
            b.month_start
    ),
    plan_types(sort_order, plan_type) as (
        values
            (1, 'Sesión'),
            (2, 'Mensualidad'),
            (3, 'Tiquetera'),
            (4, 'Sin plan')
    ),
    plan_counts as (
        select
            p.plan_type,
            count(*) as entries,
            count(distinct p.client_id) as people
        from period_rows p
        group by p.plan_type
    ),
    plan_json as (
        select coalesce(
            jsonb_agg(
                jsonb_build_object(
                    'type', t.plan_type,
                    'people', coalesce(c.people, 0),
                    'entries', coalesce(c.entries, 0),
                    'percentage', case
                        when m.period_entries = 0 then 0
                        else round(
                            coalesce(c.entries, 0)::numeric
                            * 100
                            / m.period_entries,
                            1
                        )
                    end
                )
                order by t.sort_order
            ),
            '[]'::jsonb
        ) as value
        from plan_types t
        left join plan_counts c
          on c.plan_type = t.plan_type
        cross join metric_values m
    ),
    daily_days as (
        select generate_series(
            b.chart_start::timestamp,
            b.today_date::timestamp,
            interval '1 day'
        )::date as day
        from bounds b
    ),
    daily_counts as (
        select
            c.local_day as day,
            count(*) as entries
        from classified c
        cross join bounds b
        where c.local_day between
            b.chart_start and b.today_date
        group by c.local_day
    ),
    daily_json as (
        select coalesce(
            jsonb_agg(
                jsonb_build_object(
                    'date', d.day,
                    'count', coalesce(c.entries, 0)
                )
                order by d.day
            ),
            '[]'::jsonb
        ) as value
        from daily_days d
        left join daily_counts c
          on c.day = d.day
    ),
    weekday_counts as (
        select
            extract(isodow from p.local_at)::integer
                as weekday_number,
            case extract(isodow from p.local_at)::integer
                when 1 then 'Lunes'
                when 2 then 'Martes'
                when 3 then 'Miércoles'
                when 4 then 'Jueves'
                when 5 then 'Viernes'
                when 6 then 'Sábado'
                else 'Domingo'
            end as weekday_name,
            count(*) as entries
        from period_rows p
        group by extract(isodow from p.local_at)
    ),
    peak_hours as (
        select
            extract(hour from p.local_at)::integer as hour_number,
            count(*) as entries
        from period_rows p
        group by extract(hour from p.local_at)
    ),
    active_clients as (
        select c.id
        from public.clients c
        where c.gym_id = p_gym_id
          and c.active = true
    ),
    recent_visits as (
        select
            c.client_id,
            max(c.local_day) as last_visit
        from classified c
        cross join bounds b
        where c.local_day between
            b.today_date - 29 and b.today_date
        group by c.client_id
    ),
    inactivity_values as (
        select
            count(a.id) as active_clients,
            count(a.id) filter (
                where r.last_visit is null
                   or r.last_visit < v_today - 6
            ) as inactive_7,
            count(a.id) filter (
                where r.last_visit is null
                   or r.last_visit < v_today - 14
            ) as inactive_15,
            count(a.id) filter (
                where r.last_visit is null
                   or r.last_visit < v_today - 29
            ) as inactive_30
        from active_clients a
        left join recent_visits r
          on r.client_id = a.id
    ),
    top_rows as (
        select
            p.client_id,
            max(p.document) as document,
            max(p.client_name) as client_name,
            count(*) as entries,
            max(p.local_day) as last_visit,
            (
                array_agg(
                    p.plan_type
                    order by p.local_at desc
                )
            )[1] as plan_type
        from period_rows p
        group by p.client_id
        order by count(*) desc, max(p.client_name)
        limit 10
    ),
    top_json as (
        select coalesce(
            jsonb_agg(
                jsonb_build_object(
                    'client_id', t.client_id,
                    'document', t.document,
                    'client_name', t.client_name,
                    'plan_type', t.plan_type,
                    'entries', t.entries,
                    'last_visit', t.last_visit
                )
                order by t.entries desc, t.client_name
            ),
            '[]'::jsonb
        ) as value
        from top_rows t
    )
    select jsonb_build_object(
        'days', v_days,
        'generated_at', now(),
        'metrics', jsonb_build_object(
            'today_entries', m.today_entries,
            'today_unique', m.today_unique,
            'week_entries', m.week_entries,
            'week_unique', m.week_unique,
            'month_entries', m.month_entries,
            'month_unique', m.month_unique,
            'period_entries', m.period_entries,
            'period_unique', m.period_unique,
            'previous_entries', m.previous_entries,
            'daily_average', round(
                m.period_entries::numeric / v_days,
                1
            ),
            'trend_percentage', case
                when m.previous_entries = 0 then
                    case
                        when m.period_entries = 0 then 0
                        else 100
                    end
                else round(
                    (
                        m.period_entries
                        - m.previous_entries
                    )::numeric
                    * 100
                    / m.previous_entries,
                    1
                )
            end,
            'busiest_weekday', coalesce(
                (
                    select w.weekday_name
                    from weekday_counts w
                    order by
                        w.entries desc,
                        w.weekday_number
                    limit 1
                ),
                'Sin datos'
            ),
            'peak_hour', coalesce(
                (
                    select
                        lpad(h.hour_number::text, 2, '0')
                        || ':00 – '
                        || lpad(h.hour_number::text, 2, '0')
                        || ':59'
                    from peak_hours h
                    order by
                        h.entries desc,
                        h.hour_number
                    limit 1
                ),
                'Sin datos'
            ),
            'active_clients', i.active_clients,
            'inactive_7', i.inactive_7,
            'inactive_15', i.inactive_15,
            'inactive_30', i.inactive_30
        ),
        'plan_breakdown', p.value,
        'daily_series', d.value,
        'top_clients', t.value
    )
    into v_result
    from metric_values m
    cross join inactivity_values i
    cross join plan_json p
    cross join daily_json d
    cross join top_json t;

    return v_result;
end;
$$;

revoke all on function public.get_attendance_statistics(
    uuid,
    integer
) from public;

grant execute on function public.get_attendance_statistics(
    uuid,
    integer
) to authenticated;
