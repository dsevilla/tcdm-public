package cursohadoop.wordcount;

import java.io.IOException;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.StreamSupport;

import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Reducer;

public class WordCountReducer extends Reducer<Text, LongWritable, Text, LongWritable>
{
    @Override
    public void reduce(Text key, Iterable<LongWritable> values, Context ctxt) throws IOException, InterruptedException
    {
        AtomicLong sum = new AtomicLong(0);
        StreamSupport.stream(values.spliterator(), true)
            .forEach(v -> sum.addAndGet(v.get()));
        ctxt.write(key, new LongWritable(sum.get()));
    }
}
